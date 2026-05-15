import pytest
from tinyvm.tokeniser import TOKEN_TO_ID, BOS, EOS, NEWLINE, DIGIT_TOKENS, MINUS
from tinyvm.isa import Op, Instruction, Program
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
