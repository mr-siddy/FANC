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


import pytest
from tinyvm.isa import Instruction, Program


def test_instruction_is_frozen():
    inst = Instruction(op=Op.LOAD, args=(0, 5))
    with pytest.raises((AttributeError, TypeError)):
        inst.op = Op.ADD  # type: ignore[misc]


def test_instruction_default_label_and_target_are_none():
    inst = Instruction(op=Op.ADD, args=(0, 1, 2))
    assert inst.label is None
    assert inst.target is None


def test_program_precomputes_label_index():
    insts = (
        Instruction(op=Op.LOAD, args=(0, 1), label="L0"),
        Instruction(op=Op.ADD, args=(0, 0, 0)),
        Instruction(op=Op.JMP, args=(), target="L0"),
        Instruction(op=Op.HALT, args=(), label="END"),
    )
    p = Program.build(insts)
    assert p.label_index == {"L0": 0, "END": 3}
    assert len(p.instructions) == 4


def test_program_build_rejects_duplicate_labels():
    insts = (
        Instruction(op=Op.NOP, args=(), label="L0"),
        Instruction(op=Op.NOP, args=(), label="L0"),
    )
    with pytest.raises(ValueError, match="duplicate label"):
        Program.build(insts)


def test_program_label_index_is_immutable():
    p = Program.build((
        Instruction(op=Op.LOAD, args=(0, 1), label="L0"),
    ))
    with pytest.raises(TypeError):
        p.label_index["NEW"] = 99  # type: ignore[index]
