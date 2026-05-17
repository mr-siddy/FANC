import hashlib
import json
import random
from pathlib import Path

from tinyvm.data.configs import TIER0
from tinyvm.data.emit import _build_renders, _emit_split, _row_seed
from tinyvm.data.schema import RenderedPrompt
from tinyvm.generators import gen_register_trace
from tinyvm.interpreter import run


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


def test_build_renders_produces_expected_modes():
    p = gen_register_trace(n=8, k=2, rng=random.Random(0))
    trace = run(p)
    out = _build_renders(p, trace, ("direct",))
    assert set(out.keys()) == {"direct"}
    assert isinstance(out["direct"], RenderedPrompt)
    assert len(out["direct"].input_ids) > 0
    assert len(out["direct"].target_ids) > 0
    # Must contain at least one register token (R0..R7) — seed-independent.
    assert any(f"R{i}" in out["direct"].input_text for i in range(8)), \
        f"input_text missing register tokens: {out['direct'].input_text!r}"


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


def test_emit_split_writes_n_rows_to_file(tmp_path: Path):
    out_path = tmp_path / "train.jsonl"
    n, h = _emit_split(TIER0, out_path, split="train", bucket=None,
                       n_rows=5, seed_base=0)
    assert n == 5
    assert isinstance(h, str) and len(h) == 64
    assert out_path.exists()
    lines = out_path.read_text().splitlines()
    assert len(lines) == 5
    # Each line is a valid JSON object with the expected top-level keys.
    for line in lines:
        row = json.loads(line)
        assert set(row.keys()) == {"meta", "program", "trace", "renders"}
        assert row["meta"]["tier"] == "tier0"
        assert row["meta"]["split"] == "train"
        assert row["meta"]["bucket"] is None


def test_emit_split_sha256_matches_file_content(tmp_path: Path):
    out_path = tmp_path / "train.jsonl"
    _, h = _emit_split(TIER0, out_path, split="train", bucket=None,
                       n_rows=3, seed_base=0)
    recomputed = hashlib.sha256(out_path.read_bytes()).hexdigest()
    assert h == recomputed


def test_emit_split_eval_uses_fixed_axes(tmp_path: Path):
    bucket = TIER0.eval_buckets[0]
    out_path = tmp_path / f"{bucket.name}.jsonl"
    _emit_split(TIER0, out_path, split="eval", bucket=bucket,
                n_rows=3, seed_base=0)
    for line in out_path.read_text().splitlines():
        row = json.loads(line)
        assert row["meta"]["split"] == "eval"
        assert row["meta"]["bucket"] == bucket.name
        assert row["meta"]["axes"] == dict(bucket.fixed_axes)


def test_emit_split_is_deterministic(tmp_path: Path):
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    _emit_split(TIER0, a, split="train", bucket=None, n_rows=4, seed_base=42)
    _emit_split(TIER0, b, split="train", bucket=None, n_rows=4, seed_base=42)
    assert a.read_bytes() == b.read_bytes()
