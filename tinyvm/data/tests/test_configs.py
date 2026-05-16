import random
import pytest

from tinyvm.data.configs import EvalBucket, DatasetConfig, TIER0, TIER1
from tinyvm.interpreter import run
from tinyvm.verifier import validate


def test_eval_bucket_is_frozen():
    b = EvalBucket(name="len_8", size=20_000, fixed_axes={"n": 8, "k": 4})
    with pytest.raises((AttributeError, TypeError)):
        b.size = 99  # type: ignore[misc]


def test_dataset_config_holds_required_fields():
    cfg = DatasetConfig(
        tier="tier0",
        train_size=100,
        train_axes=lambda rng: {"n": 4},
        eval_buckets=(EvalBucket(name="all", size=10, fixed_axes={"n": 4}),),
        build=lambda rng, axes: None,   # type: ignore[arg-type]
        renders=("direct",),
    )
    assert cfg.tier == "tier0"
    assert cfg.train_size == 100
    assert cfg.eval_buckets[0].size == 10
    assert cfg.renders == ("direct",)


def test_tier0_config_metadata():
    assert TIER0.tier == "tier0"
    assert TIER0.train_size == 100_000
    assert TIER0.eval_buckets == (EvalBucket(name="all", size=10_000, fixed_axes={"n": 8}),)
    assert TIER0.renders == ("direct",)


def test_tier0_build_produces_valid_programs():
    for seed in range(20):
        rng = random.Random(seed)
        axes = TIER0.train_axes(rng)
        assert 4 <= axes["n"] <= 8
        p = TIER0.build(rng, axes)
        assert validate(p)
        assert run(p).halted


def test_tier1_config_metadata():
    assert TIER1.tier == "tier1"
    assert TIER1.train_size == 200_000
    bucket_names = tuple(b.name for b in TIER1.eval_buckets)
    assert bucket_names == ("len_8", "len_16", "len_32", "len_48", "len_64", "len_96", "len_128")
    for b in TIER1.eval_buckets:
        assert b.size == 20_000
        assert b.fixed_axes["k"] == 4
    assert TIER1.renders == ("direct",)


def test_tier1_build_produces_valid_programs():
    for seed in range(20):
        rng = random.Random(seed)
        axes = TIER1.train_axes(rng)
        assert 8 <= axes["n"] <= 32
        assert axes["k"] in (2, 4, 8)
        p = TIER1.build(rng, axes)
        assert validate(p)
        assert run(p).halted
