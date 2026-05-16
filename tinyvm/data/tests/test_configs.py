import random
import pytest

from tinyvm.data.configs import EvalBucket, DatasetConfig


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
