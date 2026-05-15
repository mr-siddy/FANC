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
