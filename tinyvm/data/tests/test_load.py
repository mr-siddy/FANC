# tinyvm/data/tests/test_load.py
import pytest
from pathlib import Path

from tinyvm.data.load import load_jsonl, load_split, load_prompts, load_manifest
from tinyvm.data.emit import emit
from tinyvm.data.configs import EvalBucket, DatasetConfig
from tinyvm.data.configs import _tier0_train_axes, _tier0_build


def _tiny_config():
    return DatasetConfig(
        tier="tier0",
        train_size=4,
        train_axes=_tier0_train_axes,
        eval_buckets=(EvalBucket(name="all", size=3, fixed_axes={"n": 8}),),
        build=_tier0_build,
        renders=("direct",),
    )


def test_load_jsonl_yields_rows(tmp_path: Path):
    emit(_tiny_config(), tmp_path, seed_base=0)
    rows = list(load_jsonl(tmp_path / "tier0" / "train.jsonl"))
    assert len(rows) == 4
    # Each row is a Row NamedTuple from schema.py.
    from tinyvm.data.schema import Row
    assert all(isinstance(r, Row) for r in rows)
    # The first row's program is well-formed.
    assert len(rows[0].program.instructions) > 0


def test_load_split_train(tmp_path: Path):
    emit(_tiny_config(), tmp_path, seed_base=0)
    rows = list(load_split(tmp_path / "tier0", split="train"))
    assert len(rows) == 4


def test_load_split_eval_requires_bucket(tmp_path: Path):
    emit(_tiny_config(), tmp_path, seed_base=0)
    with pytest.raises(ValueError, match="bucket required"):
        list(load_split(tmp_path / "tier0", split="eval"))


def test_load_split_eval_bucket(tmp_path: Path):
    emit(_tiny_config(), tmp_path, seed_base=0)
    rows = list(load_split(tmp_path / "tier0", split="eval", bucket="all"))
    assert len(rows) == 3
    assert all(r.meta.bucket == "all" for r in rows)


def test_load_prompts_yields_id_tuples(tmp_path: Path):
    emit(_tiny_config(), tmp_path, seed_base=0)
    pairs = list(load_prompts(tmp_path / "tier0" / "train.jsonl", mode="direct"))
    assert len(pairs) == 4
    for input_ids, target_ids in pairs:
        assert isinstance(input_ids, list)
        assert isinstance(target_ids, list)
        assert all(isinstance(x, int) for x in input_ids)
        assert all(isinstance(x, int) for x in target_ids)


def test_load_prompts_raises_on_unknown_mode(tmp_path: Path):
    emit(_tiny_config(), tmp_path, seed_base=0)
    with pytest.raises(KeyError):
        list(load_prompts(tmp_path / "tier0" / "train.jsonl", mode="not_a_mode"))


def test_load_manifest_returns_dict(tmp_path: Path):
    emit(_tiny_config(), tmp_path, seed_base=0)
    manifest = load_manifest(tmp_path / "tier0")
    assert manifest["tier"] == "tier0"
    assert "files" in manifest


def test_load_manifest_raises_on_missing(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_manifest(tmp_path / "nonexistent")
