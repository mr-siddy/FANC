import pytest
from tinyvm.tokeniser import TOKEN_TO_ID, BOS, EOS, NEWLINE, DIGIT_TOKENS, MINUS
from tinyvm.isa import Op, Instruction, Program, STACK_DEPTH
from tinyvm.verifier import score_output, validate


def _ids(*toks: str) -> list[int]:
    return [TOKEN_TO_ID[t] for t in toks]


def test_score_output_returns_1_on_exact_value_match():
    a = _ids(BOS, "3", NEWLINE, "5", NEWLINE, EOS)
    b = _ids(BOS, "3", NEWLINE, "5", NEWLINE, EOS)
    assert score_output(a, b) == 1.0


def test_score_output_returns_0_on_value_mismatch():
    a = _ids(BOS, "3", NEWLINE, EOS)
    b = _ids(BOS, "4", NEWLINE, EOS)
    assert score_output(a, b) == 0.0


def test_score_output_returns_0_on_length_mismatch():
    a = _ids(BOS, "3", NEWLINE, EOS)
    b = _ids(BOS, "3", NEWLINE, "5", NEWLINE, EOS)
    assert score_output(a, b) == 0.0


def test_score_output_negative_values():
    a = _ids(BOS, MINUS, "5", NEWLINE, EOS)
    b = _ids(BOS, MINUS, "5", NEWLINE, EOS)
    assert score_output(a, b) == 1.0


def test_validate_accepts_clean_program():
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 5)),
        Instruction(Op.ADD, args=(1, 0, 0)),
        Instruction(Op.PRINT, args=(1,)),
        Instruction(Op.HALT),
    ))
    assert validate(p) is True


def test_validate_rejects_unknown_label_target():
    p = Program.build((
        Instruction(Op.JMP, args=(), target="UNKNOWN"),
    ))
    assert validate(p) is False


def test_validate_rejects_wrong_opcode_arity():
    # ADD requires 3 args; pass 2.
    p = Program.build((
        Instruction(Op.ADD, args=(0, 1)),
    ))
    assert validate(p) is False


def test_validate_rejects_print_without_write():
    p = Program.build((
        Instruction(Op.PRINT, args=(3,)),
    ))
    assert validate(p) is False


def test_validate_accepts_print_after_write():
    p = Program.build((
        Instruction(Op.LOAD, args=(3, 5)),
        Instruction(Op.PRINT, args=(3,)),
    ))
    assert validate(p) is True


def test_validate_handles_branch_paths():
    # Both arms write R3 before PRINT.
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 0)),
        Instruction(Op.JZ, args=(0,), target="ELSE"),
        Instruction(Op.LOAD, args=(3, 1)),    # then arm
        Instruction(Op.JMP, args=(), target="JOIN"),
        Instruction(Op.LOAD, args=(3, 2), label="ELSE"),  # else arm
        Instruction(Op.PRINT, args=(3,), label="JOIN"),
    ))
    assert validate(p) is True


def test_validate_rejects_branch_with_unwritten_arm():
    # ELSE arm doesn't write R3.
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 0)),
        Instruction(Op.JZ, args=(0,), target="ELSE"),
        Instruction(Op.LOAD, args=(3, 1)),
        Instruction(Op.JMP, args=(), target="JOIN"),
        Instruction(Op.NOP, label="ELSE"),
        Instruction(Op.PRINT, args=(3,), label="JOIN"),
    ))
    assert validate(p) is False


def test_validate_rejects_pop_without_push():
    p = Program.build((Instruction(Op.LOAD, args=(0, 1)), Instruction(Op.POP, args=(0,))))
    assert validate(p) is False


def test_validate_accepts_balanced_push_pop():
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 1)),
        Instruction(Op.PUSH, args=(0,)),
        Instruction(Op.POP, args=(1,)),
    ))
    assert validate(p) is True


def test_validate_rejects_stack_overflow_by_construction():
    insts = [Instruction(Op.LOAD, args=(0, 1))]
    insts += [Instruction(Op.PUSH, args=(0,)) for _ in range(STACK_DEPTH + 1)]
    p = Program.build(tuple(insts))
    assert validate(p) is False


def test_validate_loop_counter_uniqueness_smoke():
    # A program with a single explicit loop and a single counter — passes.
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 3)),                          # counter Rc=R0
        Instruction(Op.LOAD, args=(1, 1)),                          # R_one
        Instruction(Op.SUB, args=(0, 0, 1), label="L"),
        Instruction(Op.JZ, args=(0,), target="END"),
        Instruction(Op.JMP, args=(), target="L"),
        Instruction(Op.NOP, label="END"),
    ))
    assert validate(p) is True
