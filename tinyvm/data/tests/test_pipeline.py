# tinyvm/data/tests/test_pipeline.py
"""End-to-end pipeline tests. Spec §10."""
import random
from pathlib import Path

from tinyvm.data.configs import EvalBucket, DatasetConfig
from tinyvm.data.configs import (
    _tier0_train_axes, _tier0_build,
    _tier1_train_axes, _tier1_build,
)
from tinyvm.data.emit import emit
from tinyvm.data.load import load_jsonl
from tinyvm.interpreter import run


def _tiny_tier0():
    return DatasetConfig(
        tier="tier0", train_size=10, train_axes=_tier0_train_axes,
        eval_buckets=(EvalBucket(name="all", size=5, fixed_axes={"n": 8}),),
        build=_tier0_build, renders=("direct",),
    )


def _tiny_tier1():
    return DatasetConfig(
        tier="tier1", train_size=10, train_axes=_tier1_train_axes,
        eval_buckets=(EvalBucket(name="len_16", size=5, fixed_axes={"n": 16, "k": 4}),),
        build=_tier1_build, renders=("direct",),
    )


def test_trace_replay_tier0(tmp_path: Path):
    """Every loaded row's program re-runs to produce the trace's output."""
    emit(_tiny_tier0(), tmp_path, seed_base=0)
    for row in load_jsonl(tmp_path / "tier0" / "train.jsonl"):
        replayed = run(row.program)
        assert replayed.output == row.trace.output
        assert replayed.halted == row.trace.halted


def test_trace_replay_tier1(tmp_path: Path):
    emit(_tiny_tier1(), tmp_path, seed_base=0)
    for row in load_jsonl(tmp_path / "tier1" / "train.jsonl"):
        replayed = run(row.program)
        assert replayed.output == row.trace.output


def test_seed_reproducibility_per_row(tmp_path: Path):
    """Each row's program is reconstructable from row.meta.seed + row.meta.axes."""
    cfg = _tiny_tier1()
    emit(cfg, tmp_path, seed_base=0)
    for row in load_jsonl(tmp_path / "tier1" / "train.jsonl"):
        replayed = cfg.build(random.Random(row.meta.seed), row.meta.axes)
        assert replayed == row.program, f"row reconstruction failed for seed={row.meta.seed}"
