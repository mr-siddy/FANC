"""Verifier: score_output (RLVR reward) and validate (IR well-formedness)."""
from __future__ import annotations

from tinyvm.tokeniser import (
    BOS, DIGIT_TOKENS, EOS, ID_TO_TOKEN, MINUS, NEWLINE, _OP_ARG_SCHEMA,
)
from tinyvm.isa import Program


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


# Stubs for the remaining checks — Tasks 18-21 will implement.
def _check_print_predecessors(program: Program, userop_signatures: dict[str, set[int]] | None) -> None:
    pass


def _check_stack_balance(program: Program) -> None:
    pass


def _check_loop_counter_uniqueness(program: Program) -> None:
    pass
