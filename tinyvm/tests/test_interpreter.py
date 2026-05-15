import pytest

from tinyvm.isa import Op, Instruction, Program, VAL_MIN, VAL_MAX, STACK_DEPTH
from tinyvm.interpreter import run, InterpreterError, ExecutionTrace


def _prog(*insts: Instruction) -> Program:
    return Program.build(tuple(insts))


def test_initial_register_state_is_zero():
    p = _prog(Instruction(Op.PRINT, args=(3,)), Instruction(Op.HALT))
    trace = run(p)
    assert trace.output == [0]
    assert trace.halted is True


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


def test_eq_returns_one_when_equal():
    p = _prog(
        Instruction(Op.LOAD, args=(0, 5)),
        Instruction(Op.LOAD, args=(1, 5)),
        Instruction(Op.EQ, args=(2, 0, 1)),
    )
    trace = run(p)
    assert trace.steps[-1].regs[2] == 1


def test_eq_returns_zero_when_unequal():
    p = _prog(
        Instruction(Op.LOAD, args=(0, 5)),
        Instruction(Op.LOAD, args=(1, 6)),
        Instruction(Op.EQ, args=(2, 0, 1)),
    )
    trace = run(p)
    assert trace.steps[-1].regs[2] == 0


def test_lt_strict_less_than():
    p = _prog(
        Instruction(Op.LOAD, args=(0, 3)),
        Instruction(Op.LOAD, args=(1, 4)),
        Instruction(Op.LT, args=(2, 0, 1)),
        Instruction(Op.LT, args=(3, 1, 0)),
        Instruction(Op.LT, args=(4, 0, 0)),
    )
    trace = run(p)
    regs = trace.steps[-1].regs
    assert regs[2] == 1 and regs[3] == 0 and regs[4] == 0


def test_jz_taken_when_register_is_zero():
    p = _prog(
        Instruction(Op.LOAD, args=(0, 0)),
        Instruction(Op.JZ, args=(0,), target="END"),
        Instruction(Op.LOAD, args=(1, 99)),       # skipped
        Instruction(Op.NOP, label="END"),
    )
    trace = run(p)
    assert trace.steps[-1].regs[1] == 0


def test_jz_not_taken_when_register_is_nonzero():
    p = _prog(
        Instruction(Op.LOAD, args=(0, 1)),
        Instruction(Op.JZ, args=(0,), target="END"),
        Instruction(Op.LOAD, args=(1, 99)),       # executed
        Instruction(Op.NOP, label="END"),
    )
    trace = run(p)
    assert trace.steps[-1].regs[1] == 99


def test_jmp_unconditional():
    p = _prog(
        Instruction(Op.JMP, args=(), target="END"),
        Instruction(Op.LOAD, args=(0, 99)),       # skipped
        Instruction(Op.NOP, label="END"),
    )
    trace = run(p)
    assert trace.steps[-1].regs[0] == 0


def test_fall_off_end_halts_implicitly():
    p = _prog(Instruction(Op.LOAD, args=(0, 1)))
    trace = run(p)
    assert trace.halted is True
    assert trace.steps[-1].regs[0] == 1


def test_push_pop_round_trip():
    p = _prog(
        Instruction(Op.LOAD, args=(0, 42)),
        Instruction(Op.PUSH, args=(0,)),
        Instruction(Op.LOAD, args=(0, 0)),         # clobber R0
        Instruction(Op.POP, args=(1,)),            # R1 receives 42
    )
    trace = run(p)
    assert trace.steps[-1].regs[1] == 42


def test_push_overflow_raises():
    insts = [Instruction(Op.LOAD, args=(0, 1))]
    insts += [Instruction(Op.PUSH, args=(0,)) for _ in range(STACK_DEPTH + 1)]
    p = _prog(*insts)
    with pytest.raises(InterpreterError, match="stack overflow"):
        run(p)


def test_pop_underflow_raises():
    p = _prog(Instruction(Op.POP, args=(0,)))
    with pytest.raises(InterpreterError, match="stack underflow"):
        run(p)


def test_print_emits_register_value():
    p = _prog(
        Instruction(Op.LOAD, args=(0, 9)),
        Instruction(Op.PRINT, args=(0,)),
        Instruction(Op.LOAD, args=(0, -5)),
        Instruction(Op.PRINT, args=(0,)),
        Instruction(Op.HALT),
    )
    trace = run(p)
    assert trace.output == [9, -5]


def test_halt_stops_execution_before_remaining_instructions():
    p = _prog(
        Instruction(Op.LOAD, args=(0, 1)),
        Instruction(Op.HALT),
        Instruction(Op.LOAD, args=(0, 99)),  # should NOT execute
    )
    trace = run(p)
    assert trace.steps[-1].regs[0] == 1
    assert trace.halted is True


def test_step_cap_raises():
    p = _prog(
        Instruction(Op.JMP, args=(), target="L", label="L"),
    )
    with pytest.raises(InterpreterError, match="step cap"):
        run(p, step_cap=100)


def test_step_cap_none_disables_the_cap():
    p = _prog(
        Instruction(Op.LOAD, args=(0, 5), label="L"),
        Instruction(Op.SUB, args=(0, 0, 0)),
    )
    trace = run(p, step_cap=None)
    assert trace.halted is True


def test_userop_raises_on_execute():
    p = _prog(Instruction(Op.USEROP_0, args=(0, 1)))
    with pytest.raises(InterpreterError, match="userop"):
        run(p)
