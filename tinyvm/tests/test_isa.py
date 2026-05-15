from tinyvm.isa import (
    Op, NUM_REGS, VAL_MIN, VAL_MAX,
    LITERAL_MIN, LITERAL_MAX, STACK_DEPTH, DEFAULT_STEP_CAP,
)


def test_constants_match_spec():
    assert NUM_REGS == 8
    assert VAL_MIN == -1024
    assert VAL_MAX == 1023
    assert LITERAL_MIN == -127
    assert LITERAL_MAX == 127
    assert STACK_DEPTH == 16
    assert DEFAULT_STEP_CAP == 1_000_000


def test_op_enum_has_16_base_ops_and_5_userop_slots():
    base_ops = [
        Op.LOAD, Op.MOV, Op.ADD, Op.SUB, Op.MUL, Op.DIV,
        Op.NEG, Op.EQ, Op.LT, Op.JZ, Op.JMP,
        Op.PUSH, Op.POP, Op.PRINT, Op.NOP, Op.HALT,
    ]
    assert len(base_ops) == 16
    assert [int(op) for op in base_ops] == list(range(16))
    userop_slots = [Op.USEROP_0, Op.USEROP_1, Op.USEROP_2, Op.USEROP_3, Op.USEROP_4]
    assert [int(op) for op in userop_slots] == list(range(16, 21))


def test_op_is_userop_helper():
    assert Op.USEROP_0.is_userop()
    assert Op.USEROP_4.is_userop()
    assert not Op.LOAD.is_userop()
    assert not Op.HALT.is_userop()
