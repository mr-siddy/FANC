import pytest

from tinyvm.isa import Op, Instruction, Program, VAL_MIN, VAL_MAX
from tinyvm.interpreter import run, InterpreterError, ExecutionTrace


def _prog(*insts: Instruction) -> Program:
    return Program.build(tuple(insts))


def test_initial_register_state_is_zero():
    pytest.skip("PRINT/HALT land in Tasks 7-8")


def test_load_then_mov():
    p = _prog(
        Instruction(Op.LOAD, args=(0, 7)),
        Instruction(Op.MOV, args=(1, 0)),
    )
    trace = run(p)
    assert trace.steps[-1].regs[0] == 7
    assert trace.steps[-1].regs[1] == 7


def test_add_sub_mul_neg():
    p = _prog(
        Instruction(Op.LOAD, args=(0, 3)),
        Instruction(Op.LOAD, args=(1, 4)),
        Instruction(Op.ADD, args=(2, 0, 1)),   # R2 = 7
        Instruction(Op.SUB, args=(3, 1, 0)),   # R3 = 1
        Instruction(Op.MUL, args=(4, 2, 3)),   # R4 = 7
        Instruction(Op.NEG, args=(5, 4)),      # R5 = -7
    )
    trace = run(p)
    regs = trace.steps[-1].regs
    assert regs[2] == 7 and regs[3] == 1 and regs[4] == 7 and regs[5] == -7


def test_arithmetic_clamps_to_value_range():
    p = _prog(
        Instruction(Op.LOAD, args=(0, 100)),
        Instruction(Op.MUL, args=(1, 0, 0)),   # 10_000 -> VAL_MAX=1023
    )
    trace = run(p)
    assert trace.steps[-1].regs[1] == VAL_MAX


def test_div_by_zero_returns_zero():
    p = _prog(
        Instruction(Op.LOAD, args=(0, 10)),
        Instruction(Op.LOAD, args=(1, 0)),
        Instruction(Op.DIV, args=(2, 0, 1)),
    )
    trace = run(p)
    assert trace.steps[-1].regs[2] == 0


def test_div_truncates_toward_zero():
    p = _prog(
        Instruction(Op.LOAD, args=(0, 7)),
        Instruction(Op.LOAD, args=(1, 2)),
        Instruction(Op.DIV, args=(2, 0, 1)),
    )
    trace = run(p)
    assert trace.steps[-1].regs[2] == 3
