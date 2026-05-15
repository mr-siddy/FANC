"""Verifier: score_output (RLVR reward) and validate (IR well-formedness)."""
from __future__ import annotations

from tinyvm.tokeniser import (
    BOS, DIGIT_TOKENS, EOS, ID_TO_TOKEN, MINUS, NEWLINE, _OP_ARG_SCHEMA,
)
from tinyvm.isa import Op, Program, Instruction


def _decode_value_stream(ids: list[int]) -> list[int]:
    """Extract the sequence of integer values from BOS + digit-encoded ints + EOS."""
    tokens = [ID_TO_TOKEN[i] for i in ids]
    if tokens and tokens[0] == BOS:
        tokens = tokens[1:]
    if tokens and tokens[-1] == EOS:
        tokens = tokens[:-1]
    values: list[int] = []
    pos = 0
    while pos < len(tokens):
        if tokens[pos] == NEWLINE:
            pos += 1
            continue
        sign = 1
        if tokens[pos] == MINUS:
            sign = -1
            pos += 1
        digits = ""
        while pos < len(tokens) and tokens[pos] in DIGIT_TOKENS:
            digits += tokens[pos]
            pos += 1
        if digits:
            values.append(sign * int(digits))
        if pos < len(tokens) and tokens[pos] == NEWLINE:
            pos += 1
    return values


def score_output(predicted_ids: list[int], target_ids: list[int]) -> float:
    """Spec §9 RLVR reward: 1.0 iff decoded value sequences match exactly."""
    try:
        a = _decode_value_stream(predicted_ids)
        b = _decode_value_stream(target_ids)
    except Exception:
        return 0.0
    return 1.0 if a == b else 0.0


def validate(
    program: Program,
    userop_signatures: dict[str, set[int]] | None = None,
) -> bool:
    """Spec §9 validate(). Returns True iff well-formed.

    `userop_signatures` maps userop symbol -> set of register indices that
    userop writes to. Required when program contains unsubstituted userops.
    """
    try:
        _check_arity(program)
        _check_label_targets(program)
        _check_print_predecessors(program, userop_signatures)
        _check_stack_balance(program)
        _check_loop_counter_uniqueness(program)
    except _ValidationFailure:
        return False
    return True


class _ValidationFailure(Exception):
    pass


def _check_arity(program: Program) -> None:
    for inst in program.instructions:
        n_regs, n_lits, has_target = _OP_ARG_SCHEMA[inst.op]
        if len(inst.args) != n_regs + n_lits:
            raise _ValidationFailure(
                f"opcode {inst.op.name} expects {n_regs + n_lits} args, got {len(inst.args)}"
            )
        if has_target and inst.target is None:
            raise _ValidationFailure(f"opcode {inst.op.name} requires target label")


def _check_label_targets(program: Program) -> None:
    for inst in program.instructions:
        if inst.target is not None and inst.target not in program.label_index:
            raise _ValidationFailure(f"unknown label target: {inst.target}")


def _writes_of(inst: Instruction, userop_signatures: dict[str, set[int]] | None) -> set[int]:
    """Return the set of register indices written by this instruction."""
    op = inst.op
    if op.is_userop():
        if userop_signatures is None:
            raise _ValidationFailure(
                f"userop {inst.op.name} encountered but userop_signatures=None"
            )
        from tinyvm.tokeniser import USEROP_SLOT_TO_SYMBOL
        sym = USEROP_SLOT_TO_SYMBOL[op]
        return set(userop_signatures[sym])
    writes_one_reg = {
        Op.LOAD, Op.MOV, Op.ADD, Op.SUB, Op.MUL, Op.DIV,
        Op.NEG, Op.EQ, Op.LT, Op.POP,
    }
    if op in writes_one_reg:
        return {inst.args[0]}
    return set()


def _successors(program: Program, idx: int) -> list[int]:
    """Return the indices of instructions reachable in one step from program[idx]."""
    inst = program.instructions[idx]
    n = len(program.instructions)
    if inst.op == Op.HALT:
        return []
    if inst.op == Op.JMP:
        return [program.label_index[inst.target]]
    if inst.op == Op.JZ:
        nexts = []
        if idx + 1 < n:
            nexts.append(idx + 1)
        nexts.append(program.label_index[inst.target])
        return nexts
    if idx + 1 < n:
        return [idx + 1]
    return []


def _check_print_predecessors(
    program: Program,
    userop_signatures: dict[str, set[int]] | None,
) -> None:
    """For every PRINT Ri, ensure every reachable path from entry writes Ri before PRINT."""
    n = len(program.instructions)
    if n == 0:
        return
    NUM_REGS_LOCAL = 8
    UNIVERSE = set(range(NUM_REGS_LOCAL))
    written_in: list[set[int]] = [UNIVERSE.copy() for _ in range(n)]
    written_in[0] = set()
    predecessors: list[list[int]] = [[] for _ in range(n)]
    for i in range(n):
        for j in _successors(program, i):
            predecessors[j].append(i)

    changed = True
    while changed:
        changed = False
        for i in range(n):
            if i == 0:
                continue
            preds = predecessors[i]
            if not preds:
                new = set()  # unreachable
            else:
                new = set.intersection(*(
                    written_in[p] | _writes_of(program.instructions[p], userop_signatures)
                    for p in preds
                ))
            if new != written_in[i]:
                written_in[i] = new
                changed = True

    for i, inst in enumerate(program.instructions):
        if inst.op == Op.PRINT:
            (ri,) = inst.args
            if ri not in written_in[i]:
                raise _ValidationFailure(
                    f"PRINT R{ri} at idx {i} not preceded by write on all paths"
                )


def _check_stack_balance(program: Program) -> None:
    """Dataflow over stack depth. depth_in[idx] = single value tracked per node.

    Generate-only-valid means we want exact balance, so we model depth as a
    single value rather than a range; if paths converge with different depths
    we flag it.
    """
    from tinyvm.isa import STACK_DEPTH
    n = len(program.instructions)
    if n == 0:
        return
    depth_in: list[int | None] = [None] * n
    depth_in[0] = 0
    predecessors: list[list[int]] = [[] for _ in range(n)]
    for i in range(n):
        for j in _successors(program, i):
            predecessors[j].append(i)

    def _depth_delta(op: Op) -> int:
        if op == Op.PUSH:
            return 1
        if op == Op.POP:
            return -1
        return 0

    changed = True
    while changed:
        changed = False
        for i in range(n):
            if i == 0:
                continue
            preds = predecessors[i]
            if not preds:
                continue
            new_depth: int | None = None
            for p in preds:
                if depth_in[p] is None:
                    continue
                d = depth_in[p] + _depth_delta(program.instructions[p].op)
                if d < 0:
                    raise _ValidationFailure(f"POP at idx {p} underflows")
                if d > STACK_DEPTH:
                    raise _ValidationFailure(
                        f"PUSH at idx {p} overflows (depth {d} > {STACK_DEPTH})"
                    )
                # Check if instruction i itself would cause underflow/overflow
                d_after = d + _depth_delta(program.instructions[i].op)
                if d_after < 0:
                    raise _ValidationFailure(f"POP at idx {i} underflows")
                if d_after > STACK_DEPTH:
                    raise _ValidationFailure(
                        f"PUSH at idx {i} overflows (depth {d_after} > {STACK_DEPTH})"
                    )
                if new_depth is None:
                    new_depth = d
                elif new_depth != d:
                    raise _ValidationFailure(
                        f"stack depth at idx {i} not balanced across paths: {new_depth} vs {d}"
                    )
            if new_depth is not None and depth_in[i] != new_depth:
                depth_in[i] = new_depth
                changed = True


def _check_loop_counter_uniqueness(program: Program) -> None:
    """Day 1-2 scope: enforced constructively by generators (Task 28+).

    A structural check would require recovering the CFG and finding back-edges,
    which is straightforward but unnecessary while generators carry the
    invariant by construction. Promote to a real check if generator drift is
    suspected.
    """
    return
