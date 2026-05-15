"""Interpreter: pure function run(Program) -> ExecutionTrace.

Semantics live here in one place (spec §6). All registers init to 0. All
arithmetic clamps to [VAL_MIN, VAL_MAX]. DIV/0 returns 0. Stack/USEROP
violations raise InterpreterError (spec §6, asymmetric error policy).
"""
from __future__ import annotations

from dataclasses import dataclass

from tinyvm.isa import (
    DEFAULT_STEP_CAP, NUM_REGS, Op, Program, STACK_DEPTH, VAL_MAX, VAL_MIN,
)


class InterpreterError(RuntimeError):
    """Raised on conditions that should never occur under generate-only-valid."""


@dataclass(frozen=True)
class StepRecord:
    pc: int
    regs: tuple[int, ...]
    stack: tuple[int, ...]
    emitted: int | None


@dataclass
class ExecutionTrace:
    steps: list[StepRecord]
    output: list[int]
    halted: bool


def _clamp(v: int) -> int:
    if v < VAL_MIN:
        return VAL_MIN
    if v > VAL_MAX:
        return VAL_MAX
    return v


def run(program: Program, step_cap: int | None = DEFAULT_STEP_CAP) -> ExecutionTrace:
    regs = [0] * NUM_REGS
    stack: list[int] = []
    steps: list[StepRecord] = []
    output: list[int] = []
    pc = 0
    n = len(program.instructions)
    step_count = 0

    while pc < n:
        if step_cap is not None and step_count >= step_cap:
            raise InterpreterError(f"step cap {step_cap} exceeded")
        step_count += 1

        executed_pc = pc
        inst = program.instructions[pc]
        op = inst.op
        args = inst.args
        next_pc = pc + 1
        emitted: int | None = None

        if op == Op.LOAD:
            i, lit = args
            regs[i] = _clamp(lit)
        elif op == Op.MOV:
            i, j = args
            regs[i] = regs[j]
        elif op == Op.ADD:
            i, j, k = args
            regs[i] = _clamp(regs[j] + regs[k])
        elif op == Op.SUB:
            i, j, k = args
            regs[i] = _clamp(regs[j] - regs[k])
        elif op == Op.MUL:
            i, j, k = args
            regs[i] = _clamp(regs[j] * regs[k])
        elif op == Op.DIV:
            i, j, k = args
            divisor = regs[k]
            if divisor == 0:
                regs[i] = 0
            else:
                q = abs(regs[j]) // abs(divisor)
                if (regs[j] < 0) ^ (divisor < 0):
                    q = -q
                regs[i] = _clamp(q)
        elif op == Op.NEG:
            i, j = args
            regs[i] = _clamp(-regs[j])
        elif op == Op.EQ:
            i, j, k = args
            regs[i] = 1 if regs[j] == regs[k] else 0
        elif op == Op.LT:
            i, j, k = args
            regs[i] = 1 if regs[j] < regs[k] else 0
        elif op == Op.JZ:
            (i,) = args
            if regs[i] == 0:
                next_pc = program.label_index[inst.target]
        elif op == Op.JMP:
            next_pc = program.label_index[inst.target]
        elif op == Op.NOP:
            pass
        elif op == Op.PUSH:
            (i,) = args
            if len(stack) >= STACK_DEPTH:
                raise InterpreterError("stack overflow")
            stack.append(regs[i])
        elif op == Op.POP:
            (i,) = args
            if not stack:
                raise InterpreterError("stack underflow")
            regs[i] = stack.pop()
        else:
            raise InterpreterError(f"unhandled op (partial impl): {op}")

        steps.append(StepRecord(
            pc=executed_pc,
            regs=tuple(regs),
            stack=tuple(stack),
            emitted=emitted,
        ))
        pc = next_pc

    return ExecutionTrace(steps=steps, output=output, halted=True)
