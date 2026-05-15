from tinyvm.tokeniser import TOKEN_TO_ID, BOS, EOS, NEWLINE, DIGIT_TOKENS, MINUS
from tinyvm.verifier import score_output


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
