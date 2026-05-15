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
