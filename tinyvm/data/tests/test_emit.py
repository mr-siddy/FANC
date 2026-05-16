from tinyvm.data.emit import _row_seed


def test_row_seed_is_deterministic():
    assert _row_seed(0, "train", None, 0) == _row_seed(0, "train", None, 0)


def test_row_seed_changes_with_seed_base():
    assert _row_seed(0, "train", None, 0) != _row_seed(1, "train", None, 0)


def test_row_seed_changes_with_split():
    assert _row_seed(0, "train", None, 0) != _row_seed(0, "eval", None, 0)


def test_row_seed_changes_with_bucket():
    assert _row_seed(0, "eval", "len_8", 0) != _row_seed(0, "eval", "len_16", 0)


def test_row_seed_changes_with_index():
    assert _row_seed(0, "train", None, 0) != _row_seed(0, "train", None, 1)


def test_row_seed_is_64_bit_unsigned_int():
    s = _row_seed(0, "train", None, 0)
    assert isinstance(s, int)
    assert 0 <= s < 2**64


import random
from tinyvm.data.emit import _build_renders
from tinyvm.data.schema import RenderedPrompt
from tinyvm.generators import gen_register_trace
from tinyvm.interpreter import run


def test_build_renders_produces_expected_modes():
    p = gen_register_trace(n=8, k=2, rng=random.Random(0))
    trace = run(p)
    out = _build_renders(p, trace, ("direct",))
    assert set(out.keys()) == {"direct"}
    assert isinstance(out["direct"], RenderedPrompt)
    assert len(out["direct"].input_ids) > 0
    assert len(out["direct"].target_ids) > 0
    assert len(out["direct"].input_text) > 0  # Contains instructions as text


def test_build_renders_handles_multiple_modes():
    p = gen_register_trace(n=8, k=2, rng=random.Random(0))
    trace = run(p)
    out = _build_renders(p, trace, ("direct", "cot"))
    assert set(out.keys()) == {"direct", "cot"}
    # CoT target should be longer than direct target (carries per-step register file).
    assert len(out["cot"].target_ids) > len(out["direct"].target_ids)


def test_build_renders_empty_modes_returns_empty_dict():
    p = gen_register_trace(n=8, k=2, rng=random.Random(0))
    trace = run(p)
    out = _build_renders(p, trace, ())
    assert out == {}


def test_build_renders_unknown_mode_raises():
    import pytest
    p = gen_register_trace(n=8, k=2, rng=random.Random(0))
    trace = run(p)
    with pytest.raises(KeyError):
        _build_renders(p, trace, ("not_a_mode",))
