"""Tokeniser: 64-token vocab + encode/decode + renderers (spec §8)."""
from __future__ import annotations

from tinyvm.isa import NUM_REGS, Op


# 1. Build the vocab as an ordered list of tokens. ID = list position.
OPCODE_TOKENS: list[str] = [op.name for op in Op if not op.is_userop()]   # 16
REGISTER_TOKENS: list[str] = [f"R{i}" for i in range(NUM_REGS)]            # 8
DIGIT_TOKENS: list[str] = [str(i) for i in range(10)]                      # 10

MINUS: str = "MINUS"
L_MARKER: str = "L"
COLON: str = "COLON"
EQUALS: str = "EQUALS"
DECOMP: str = "DECOMP"
NEWLINE: str = "NEWLINE"
BOS: str = "BOS"
EOS: str = "EOS"
PAD: str = "PAD"
QUERY: str = "?"

USEROP_TOKENS: list[str] = ["DOUBLE", "MAX", "ABS", "MOD", "SIGN"]
# Default 5 userop symbols. Parent §9.2 names XOR as the fifth; spec §12 swaps
# SIGN in by default due to XOR's decomposition cost. The token list is what's
# emitted in surface text; the underlying Op slot (USEROP_0..USEROP_4) is
# fixed regardless of which symbol is bound to which slot.

_FIXED_TOKENS: list[str] = (
    OPCODE_TOKENS
    + REGISTER_TOKENS
    + DIGIT_TOKENS
    + [MINUS, L_MARKER, COLON, EQUALS, DECOMP, NEWLINE, BOS, EOS, PAD, QUERY]
    + USEROP_TOKENS
)
# Pad the vocab to 64 with placeholder reserved tokens.
_RESERVED_TOKENS: list[str] = [f"RESERVED_{i}" for i in range(64 - len(_FIXED_TOKENS))]

_ALL_TOKENS: list[str] = _FIXED_TOKENS + _RESERVED_TOKENS

VOCAB_SIZE: int = len(_ALL_TOKENS)
assert VOCAB_SIZE == 64, f"vocab size is {VOCAB_SIZE}, expected 64"

TOKEN_TO_ID: dict[str, int] = {tok: i for i, tok in enumerate(_ALL_TOKENS)}
ID_TO_TOKEN: dict[int, str] = {i: tok for tok, i in TOKEN_TO_ID.items()}
