"""ISA: pure data — Op enum, constants, Instruction, Program (added in Task 3)."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from types import MappingProxyType
from typing import Mapping


NUM_REGS: int = 8
VAL_MIN: int = -1024
VAL_MAX: int = 1023
LITERAL_MIN: int = -127
LITERAL_MAX: int = 127
STACK_DEPTH: int = 16
DEFAULT_STEP_CAP: int = 1_000_000


class Op(IntEnum):
    # Base ISA — interpreter executes these.
    LOAD = 0
    MOV = 1
    ADD = 2
    SUB = 3
    MUL = 4
    DIV = 5
    NEG = 6
    EQ = 7
    LT = 8
    JZ = 9
    JMP = 10
    PUSH = 11
    POP = 12
    PRINT = 13
    NOP = 14
    HALT = 15
    # Userop slots — symbolic only. Interpreter raises on these (Task 8).
    # gen_userop_trace (Task 34) substitutes them with their decomposition.
    USEROP_0 = 16
    USEROP_1 = 17
    USEROP_2 = 18
    USEROP_3 = 19
    USEROP_4 = 20

    def is_userop(self) -> bool:
        return int(self) >= 16


@dataclass(frozen=True)
class Instruction:
    """A single Tiny-VM instruction."""
    op: Op
    args: tuple[int, ...] = ()
    label: str | None = None       # label *defined* at this line, e.g. "L3"
    target: str | None = None      # label *referenced* by JZ/JMP


@dataclass(frozen=True)
class Program:
    """A Tiny-VM program: instructions + precomputed label_index."""
    instructions: tuple[Instruction, ...]
    label_index: Mapping[str, int] = field(default_factory=dict)

    @classmethod
    def build(cls, instructions: tuple[Instruction, ...]) -> "Program":
        """Build a Program and precompute the label_index, rejecting duplicates."""
        idx: dict[str, int] = {}
        for i, inst in enumerate(instructions):
            if inst.label is not None:
                if inst.label in idx:
                    raise ValueError(f"duplicate label: {inst.label}")
                idx[inst.label] = i
        return cls(instructions=tuple(instructions), label_index=MappingProxyType(idx))
