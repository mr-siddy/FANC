from tinyvm.tokeniser import (
    VOCAB_SIZE, TOKEN_TO_ID, ID_TO_TOKEN, OPCODE_TOKENS, REGISTER_TOKENS,
    DIGIT_TOKENS, MINUS, L_MARKER, COLON, EQUALS, DECOMP, NEWLINE,
    BOS, EOS, PAD, QUERY, USEROP_TOKENS,
)
from tinyvm.isa import Op


def test_vocab_size_is_64():
    assert VOCAB_SIZE == 64


def test_token_id_round_trip():
    for tok, tid in TOKEN_TO_ID.items():
        assert ID_TO_TOKEN[tid] == tok


def test_token_id_assignments_are_dense():
    ids = sorted(TOKEN_TO_ID.values())
    assert ids == list(range(len(TOKEN_TO_ID)))


def test_opcode_tokens_cover_16_base_ops():
    base_ops = [op for op in Op if not op.is_userop()]
    assert len(base_ops) == 16
    for op in base_ops:
        assert op.name in OPCODE_TOKENS


def test_register_tokens_R0_through_R7():
    assert REGISTER_TOKENS == [f"R{i}" for i in range(8)]


def test_digit_tokens_0_through_9():
    assert DIGIT_TOKENS == [str(i) for i in range(10)]


def test_userop_tokens_have_five_reserved():
    assert len(USEROP_TOKENS) == 5


def test_special_tokens_exist():
    for tok in (MINUS, L_MARKER, COLON, EQUALS, DECOMP, NEWLINE, BOS, EOS, PAD, QUERY):
        assert tok in TOKEN_TO_ID
