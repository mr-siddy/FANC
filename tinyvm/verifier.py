"""Verifier: score_output (RLVR reward) and validate (IR well-formedness)."""
from __future__ import annotations

from tinyvm.tokeniser import (
    BOS, DIGIT_TOKENS, EOS, ID_TO_TOKEN, MINUS, NEWLINE,
)


def _decode_value_stream(ids: list[int]) -> list[int]:
    """Extract the sequence of integer values from BOS + digit-encoded ints + EOS."""
    tokens = [ID_TO_TOKEN[i] for i in ids]
    if tokens and tokens[0] == BOS:
        tokens = tokens[1:]
    if tokens and tokens[-1] == EOS:
        tokens = tokens[:-1]
    values: list[int] = []
    pos = 0
    while pos < len(tokens):
        if tokens[pos] == NEWLINE:
            pos += 1
            continue
        sign = 1
        if tokens[pos] == MINUS:
            sign = -1
            pos += 1
        digits = ""
        while pos < len(tokens) and tokens[pos] in DIGIT_TOKENS:
            digits += tokens[pos]
            pos += 1
        if digits:
            values.append(sign * int(digits))
        if pos < len(tokens) and tokens[pos] == NEWLINE:
            pos += 1
    return values


def score_output(predicted_ids: list[int], target_ids: list[int]) -> float:
    """Spec §9 RLVR reward: 1.0 iff decoded value sequences match exactly."""
    try:
        a = _decode_value_stream(predicted_ids)
        b = _decode_value_stream(target_ids)
    except Exception:
        return 0.0
    return 1.0 if a == b else 0.0
