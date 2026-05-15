"""Generators: build Tiny-VM programs by construction (spec §7)."""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from tinyvm.isa import Op, Instruction, Program, LITERAL_MIN, LITERAL_MAX, NUM_REGS


@dataclass(frozen=True)
class ShapingSpec:
    """Anti-shortcut knobs (spec §7.6). Defaults off."""
    flat_output_histogram: bool = False
    distractor_regs: int = 0
    randomize_print_target: bool = False
    decorrelate_length: bool = False


@dataclass(frozen=True)
class GenSpec:
    """Difficulty axes for the branched generator (spec §3.2, §7.5)."""
    n: int                          # target trajectory length
    k: int                          # active register count
    b: int = 0                      # number of branch structures
    l: int = 0                      # total loop-iteration budget
    use_stack: bool = False
    stack_frames: int = 0
    shaping: ShapingSpec = field(default_factory=ShapingSpec)


_COUNTER_OPS = [Op.ADD, Op.SUB, Op.NEG, Op.MOV]


def gen_counter(n: int, rng: random.Random) -> Program:
    """Tier 0 generator. n linear ops on R0, terminal PRINT R0, HALT.

    Op set restricted to ADD/SUB/NEG/MOV (no MUL/DIV — clamping/0-div would
    introduce non-trivial state effects that defeat the Tier 0 pipeline-sanity
    purpose). Initial LOAD seeds R0 with a small literal.
    """
    insts: list[Instruction] = []
    init_lit = rng.randint(LITERAL_MIN, LITERAL_MAX)
    insts.append(Instruction(Op.LOAD, args=(0, init_lit)))
    for _ in range(n - 1):
        op = rng.choice(_COUNTER_OPS)
        if op in (Op.ADD, Op.SUB):
            insts.append(Instruction(op, args=(0, 0, 0)))
        elif op == Op.NEG:
            insts.append(Instruction(op, args=(0, 0)))
        else:  # MOV
            insts.append(Instruction(op, args=(0, 0)))
    insts.append(Instruction(Op.PRINT, args=(0,)))
    insts.append(Instruction(Op.HALT))
    return Program.build(tuple(insts))


def _allocate_registers(k: int, rng: random.Random) -> list[int]:
    """Sample k distinct register indices uniformly from R0..R{NUM_REGS-1}.

    Per-program randomisation is essential to avoid positional bias (spec §7.1).
    """
    if not (1 <= k <= NUM_REGS):
        raise ValueError(f"k must be in [1, {NUM_REGS}], got {k}")
    return rng.sample(range(NUM_REGS), k)


_FILL_OPS: list[Op] = [
    Op.LOAD, Op.MOV, Op.ADD, Op.SUB, Op.MUL, Op.DIV, Op.NEG, Op.EQ, Op.LT,
]
_FILL_OP_ARITY: dict[Op, tuple[int, int]] = {
    Op.LOAD: (1, 1),
    Op.MOV: (2, 0),
    Op.ADD: (3, 0), Op.SUB: (3, 0), Op.MUL: (3, 0), Op.DIV: (3, 0),
    Op.NEG: (2, 0),
    Op.EQ: (3, 0), Op.LT: (3, 0),
}


def _fill_block(
    n: int,
    active: list[int],
    rng: random.Random,
    exclude: set[int] | None = None,
) -> list[Instruction]:
    """Generate `n` straight-line instructions drawn from _FILL_OPS.

    All register args are sampled from `active`. The DESTINATION register (the
    first register arg of any writing op) is sampled from `active - exclude`,
    so registers reserved as loop counters or stack-save sources are protected
    from being clobbered.
    """
    exclude = exclude or set()
    writable = [r for r in active if r not in exclude]
    assert writable, "no writable registers (active fully excluded)"
    insts: list[Instruction] = []
    for _ in range(n):
        op = rng.choice(_FILL_OPS)
        n_regs, n_lits = _FILL_OP_ARITY[op]
        args: list[int] = []
        # Destination (first reg arg) sampled from writable.
        if n_regs >= 1:
            args.append(rng.choice(writable))
        # Source regs sampled freely from active.
        for _ in range(n_regs - 1):
            args.append(rng.choice(active))
        # Literal args.
        for _ in range(n_lits):
            args.append(rng.randint(LITERAL_MIN, LITERAL_MAX))
        insts.append(Instruction(op=op, args=tuple(args)))
    return insts


def gen_register_trace(
    n: int,
    k: int,
    rng: random.Random,
    shaping: ShapingSpec | None = None,
) -> Program:
    """Tier 1 generator. Straight-line program of length n over k active regs."""
    active = _allocate_registers(k=k, rng=rng)
    body = _fill_block(n=n, active=active, rng=rng)
    # Collect registers that are written to in the body.
    written_regs = {inst.args[0] for inst in body if inst.op in _FILL_OPS}
    # If no registers are written (shouldn't happen with n >= 1), fall back to active.
    if written_regs:
        print_target = rng.choice(list(written_regs))
    else:
        print_target = rng.choice(active)
    insts: list[Instruction] = []
    insts.extend(body)
    insts.append(Instruction(Op.PRINT, args=(print_target,)))
    insts.append(Instruction(Op.HALT))
    return Program.build(tuple(insts))


class _LabelGen:
    """Fresh-label allocator; emits L0, L1, ..."""
    def __init__(self) -> None:
        self._next = 0

    def fresh(self) -> str:
        lbl = f"L{self._next}"
        self._next += 1
        return lbl


def _emit_loop_countdown(
    counter: int,
    r_one: int,
    k: int,
    body: list[Instruction],
    label_gen: _LabelGen,
) -> list[Instruction]:
    """Emit a count-down loop body executing `body` exactly k times.

    Pre-condition: r_one must be loaded with 1 before this block. Counter
    is loaded inline.
    """
    l_top = label_gen.fresh()
    l_done = label_gen.fresh()
    insts: list[Instruction] = [
        Instruction(Op.LOAD, args=(counter, k)),
    ]
    if body:
        insts.append(_with_label(body[0], l_top))
        insts.extend(body[1:])
    else:
        insts.append(Instruction(Op.NOP, label=l_top))
    insts.append(Instruction(Op.SUB, args=(counter, counter, r_one)))
    insts.append(Instruction(Op.JZ, args=(counter,), target=l_done))
    insts.append(Instruction(Op.JMP, args=(), target=l_top))
    insts.append(Instruction(Op.NOP, label=l_done))
    return insts


def _with_label(inst: Instruction, label: str) -> Instruction:
    """Return a copy of inst carrying `label`."""
    return Instruction(op=inst.op, args=inst.args, label=label, target=inst.target)


def _emit_loop_countup(
    counter: int, r_k: int, r_diff: int, r_one: int, k: int,
    body: list[Instruction], label_gen: _LabelGen,
) -> list[Instruction]:
    """Spec §7.2(b) count-up loop. Pre-condition: r_one == 1 loaded."""
    l_top = label_gen.fresh()
    l_done = label_gen.fresh()
    insts: list[Instruction] = [
        Instruction(Op.LOAD, args=(counter, 0)),
        Instruction(Op.LOAD, args=(r_k, k)),
    ]
    if body:
        insts.append(_with_label(body[0], l_top))
        insts.extend(body[1:])
    else:
        insts.append(Instruction(Op.NOP, label=l_top))
    insts.append(Instruction(Op.ADD, args=(counter, counter, r_one)))
    insts.append(Instruction(Op.SUB, args=(r_diff, r_k, counter)))
    insts.append(Instruction(Op.JZ, args=(r_diff,), target=l_done))
    insts.append(Instruction(Op.JMP, args=(), target=l_top))
    insts.append(Instruction(Op.NOP, label=l_done))
    return insts


def _emit_loop_test_at_top(
    counter: int, r_one: int, k: int,
    body: list[Instruction], label_gen: _LabelGen,
) -> list[Instruction]:
    """Spec §7.2(c) test-at-top loop. Pre-condition: r_one == 1 loaded."""
    l_top = label_gen.fresh()
    l_done = label_gen.fresh()
    insts: list[Instruction] = [
        Instruction(Op.LOAD, args=(counter, k)),
        Instruction(Op.JZ, args=(counter,), target=l_done, label=l_top),
    ]
    insts.extend(body)
    insts.append(Instruction(Op.SUB, args=(counter, counter, r_one)))
    insts.append(Instruction(Op.JMP, args=(), target=l_top))
    insts.append(Instruction(Op.NOP, label=l_done))
    return insts


def _emit_branch_if(
    cmp_op: Op, ri: int, rj: int, rc: int,
    then_block: list[Instruction], label_gen: _LabelGen,
) -> list[Instruction]:
    """Spec §7.3(a). cmp_op in {Op.LT, Op.EQ}."""
    l_after = label_gen.fresh()
    insts: list[Instruction] = [
        Instruction(cmp_op, args=(rc, ri, rj)),
        Instruction(Op.JZ, args=(rc,), target=l_after),
    ]
    insts.extend(then_block)
    insts.append(Instruction(Op.NOP, label=l_after))
    return insts


def _emit_branch_ifelse(
    cmp_op: Op, ri: int, rj: int, rc: int,
    then_block: list[Instruction], else_block: list[Instruction],
    label_gen: _LabelGen,
) -> list[Instruction]:
    """Spec §7.3(b)."""
    l_else = label_gen.fresh()
    l_after = label_gen.fresh()
    insts: list[Instruction] = [
        Instruction(cmp_op, args=(rc, ri, rj)),
        Instruction(Op.JZ, args=(rc,), target=l_else),
    ]
    insts.extend(then_block)
    insts.append(Instruction(Op.JMP, args=(), target=l_after))
    if else_block:
        insts.append(_with_label(else_block[0], l_else))
        insts.extend(else_block[1:])
    else:
        insts.append(Instruction(Op.NOP, label=l_else))
    insts.append(Instruction(Op.NOP, label=l_after))
    return insts


def _emit_branch_arith_zero(
    arith_op: Op, ri: int, rj: int, rc: int,
    then_block: list[Instruction], label_gen: _LabelGen,
) -> list[Instruction]:
    """Spec §7.3(c). arith_op in {ADD, SUB, MUL, MOV}."""
    l_after = label_gen.fresh()
    if arith_op == Op.MOV:
        insts: list[Instruction] = [Instruction(Op.MOV, args=(rc, rj))]
    else:
        insts = [Instruction(arith_op, args=(rc, ri, rj))]
    insts.append(Instruction(Op.JZ, args=(rc,), target=l_after))
    insts.extend(then_block)
    insts.append(Instruction(Op.NOP, label=l_after))
    return insts


def _emit_stack_pair(
    save: int, load_back: int, body: list[Instruction],
) -> list[Instruction]:
    """Spec §7.4(a). PUSH `save`, run body, POP into `load_back`."""
    insts: list[Instruction] = [Instruction(Op.PUSH, args=(save,))]
    insts.extend(body)
    insts.append(Instruction(Op.POP, args=(load_back,)))
    return insts


def _emit_stack_nested(
    saves: list[int], pops: list[int], body: list[Instruction],
) -> list[Instruction]:
    """Spec §7.4(b). LIFO: PUSH saves[0], ..., saves[-1]; body; POP pops[0], ..., pops[-1]."""
    assert len(saves) == len(pops), "saves and pops must have equal length"
    insts: list[Instruction] = [Instruction(Op.PUSH, args=(s,)) for s in saves]
    insts.extend(body)
    insts.extend(Instruction(Op.POP, args=(p,)) for p in pops)
    return insts


def gen_branched(spec: GenSpec, rng: random.Random) -> Program:
    """Tier 2 / Tier 4 generator (spec §7.5).

    Strategy: build a flat sequence of regions (straight-line fill, branches,
    loops, stack frames), then assemble. The iteration budget `spec.l` is
    distributed across `n_loops` loop regions, with each K drawn from the
    remaining budget.

    Active register subset is sampled per program; loop counters and stack
    spill registers are reserved within the active set.
    """
    if spec.k < 2:
        raise ValueError(
            f"gen_branched requires spec.k >= 2 (needs at least one writable register "
            f"plus r_one); got k={spec.k}. Tier 2 axis uses k in [2, 8]."
        )
    active = _allocate_registers(k=spec.k, rng=rng)
    label_gen = _LabelGen()

    # Reserve registers for housekeeping.
    # Required: r_one (constant 1), one counter per loop, scratch r_diff for count-up.
    # Plus one r_k for count-up. Plus print target.
    num_loops_target = _pick_num_loops(spec.l, rng)
    loop_Ks = _split_budget(total=spec.l, n_parts=num_loops_target, rng=rng)
    n_reserved_for_loops = num_loops_target  # one counter each
    # Plus 3 reserved housekeeping regs for count-up scratch (we always allocate them
    # so we don't have to specialise per loop template).
    needed_reserved = 1 + n_reserved_for_loops + 2  # r_one + counters + (r_k, r_diff)
    if needed_reserved > len(active):
        # Caller picked k too small; reduce loop count.
        max_loops = max(0, len(active) - 3)
        num_loops_target = min(num_loops_target, max_loops)
        loop_Ks = _split_budget(total=spec.l, n_parts=num_loops_target, rng=rng)

    reserved = list(active)
    r_one = reserved.pop()
    counter_pool = [reserved.pop() for _ in range(num_loops_target)]
    r_k = reserved.pop() if reserved else active[0]
    r_diff = reserved.pop() if reserved else active[0]

    # exclude_for_fill: protect r_one (constant 1) and loop counters from
    # being overwritten by fill blocks.  r_k / r_diff are reloaded at loop
    # entry so they are safe to clobber outside loop bodies.
    exclude_for_fill = {r_one} | set(counter_pool)
    # Inside a loop body r_k and r_diff must also be protected (they hold the
    # loop limit and diff scratch during each iteration).
    exclude_for_loop_body = exclude_for_fill | {r_k, r_diff}

    insts: list[Instruction] = [Instruction(Op.LOAD, args=(r_one, 1))]

    # Distribute the static-instruction budget across regions.
    fill_per_region = max(1, spec.n // max(1, (spec.b + num_loops_target + 1)))
    cmp_ops = [Op.LT, Op.EQ]
    arith_ops = [Op.ADD, Op.SUB, Op.MUL, Op.MOV]

    # Pick the print target from the active set, excluding r_one so the
    # safety LOAD does not clobber the constant-1 register needed by loops.
    # Emit an unconditional LOAD for it right at the start so it is
    # definitely written on EVERY path, regardless of which branches / loops
    # execute later.
    pt_candidates = [r for r in active if r != r_one]
    if not pt_candidates:
        pt_candidates = active  # k=1 edge case; no loops possible then
    print_target = rng.choice(pt_candidates)
    insts.append(Instruction(Op.LOAD, args=(print_target, rng.randint(LITERAL_MIN, LITERAL_MAX))))

    # Open with a straight-line warm-up so registers become defined.
    insts.extend(_fill_block(
        n=max(spec.k, 4), active=active, rng=rng, exclude=exclude_for_fill,
    ))

    # Emit branch regions.
    for _ in range(spec.b):
        ri, rj = rng.sample(active, 2)
        rc = rng.choice([r for r in active if r not in {ri, rj} and r not in (r_one,)] or active)
        then_block = _fill_block(
            n=fill_per_region, active=active, rng=rng, exclude=exclude_for_fill,
        )
        roll = rng.random()
        if roll < 0.2:
            arith = rng.choice(arith_ops)
            insts.extend(_emit_branch_arith_zero(arith, ri, rj, rc, then_block, label_gen))
        elif roll < 0.6:
            cmp_op = rng.choice(cmp_ops)
            insts.extend(_emit_branch_if(cmp_op, ri, rj, rc, then_block, label_gen))
        else:
            cmp_op = rng.choice(cmp_ops)
            else_block = _fill_block(
                n=fill_per_region, active=active, rng=rng, exclude=exclude_for_fill,
            )
            insts.extend(_emit_branch_ifelse(cmp_op, ri, rj, rc, then_block, else_block, label_gen))

    # Emit loop regions.
    for i in range(num_loops_target):
        counter = counter_pool[i]
        k = loop_Ks[i]
        # Choose template first so we know which housekeeping regs to protect
        # in the body.  countdown / test_at_top only use r_one + counter;
        # countup additionally uses r_k and r_diff during the loop overhead.
        # Exclude r_k / r_diff from the body only when countup is chosen AND
        # there are still writable registers left after the exclusion.
        countup_exclude = exclude_for_loop_body  # {r_one, counter_pool, r_k, r_diff}
        simple_exclude = exclude_for_fill        # {r_one, counter_pool}
        # If countup would leave no writable regs, fall back to simple templates.
        countup_writable = [r for r in active if r not in countup_exclude]
        available_templates = ["countdown", "test_at_top"]
        if countup_writable:
            available_templates.append("countup")
        template_choice = rng.choice(available_templates)
        body_exclude = countup_exclude if template_choice == "countup" else simple_exclude
        body = _fill_block(
            n=fill_per_region, active=active, rng=rng,
            exclude=body_exclude,
        )
        if template_choice == "countdown":
            insts.extend(_emit_loop_countdown(counter, r_one, k, body, label_gen))
        elif template_choice == "countup":
            insts.extend(_emit_loop_countup(counter, r_k, r_diff, r_one, k, body, label_gen))
        else:
            insts.extend(_emit_loop_test_at_top(counter, r_one, k, body, label_gen))

    # Emit stack frames if requested.
    if spec.use_stack:
        for _ in range(spec.stack_frames):
            save = rng.choice(active)
            load_back = rng.choice(active)
            body = _fill_block(
                n=max(2, fill_per_region // 2), active=active, rng=rng,
                exclude=exclude_for_fill,
            )
            insts.extend(_emit_stack_pair(save, load_back, body))

    # Final PRINT and HALT.
    # print_target was loaded unconditionally at the top, so it is always
    # written on every path.  No additional safety LOAD needed.
    insts.append(Instruction(Op.PRINT, args=(print_target,)))
    insts.append(Instruction(Op.HALT))
    return Program.build(tuple(insts))


def _was_written(insts: list[Instruction], reg: int) -> bool:
    """Quick check: is `reg` written by any instruction in `insts`?"""
    writes_one_reg = {
        Op.LOAD, Op.MOV, Op.ADD, Op.SUB, Op.MUL, Op.DIV,
        Op.NEG, Op.EQ, Op.LT, Op.POP,
    }
    return any(
        i.op in writes_one_reg and i.args and i.args[0] == reg
        for i in insts
    )


def _pick_num_loops(budget: int, rng: random.Random) -> int:
    """Pick a number of loops compatible with a total iteration budget."""
    if budget <= 0:
        return 0
    return rng.randint(1, min(4, budget))


def _split_budget(total: int, n_parts: int, rng: random.Random) -> list[int]:
    """Partition `total` into `n_parts` positive ints summing to `total`."""
    if n_parts == 0:
        return []
    if n_parts == 1:
        return [total]
    if total < n_parts:
        return [1] * n_parts
    cuts = sorted(rng.sample(range(1, total), n_parts - 1))
    parts = [cuts[0]] + [cuts[i] - cuts[i - 1] for i in range(1, n_parts - 1)] + [total - cuts[-1]]
    return parts
