"""Per-tier DatasetConfig literals. Data only — no logic.

Spec §6.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from tinyvm.isa import Program


@dataclass(frozen=True)
class EvalBucket:
    """One eval bucket. Becomes file `eval/<name>.jsonl`."""
    name: str
    size: int
    fixed_axes: dict[str, int | bool]


# A train-axes sampler: given an rng, return a dict of axes for one program.
import random as _random
TrainAxesSampler = Callable[[_random.Random], dict[str, int | bool]]

# A program builder: given an rng and concrete axes, return a Program.
ProgramBuilder = Callable[[_random.Random, dict[str, int | bool]], Program]


@dataclass(frozen=True)
class DatasetConfig:
    """A full dataset recipe. The CLI/library references by `tier` name."""
    tier: str
    train_size: int
    train_axes: TrainAxesSampler
    eval_buckets: tuple[EvalBucket, ...]
    build: ProgramBuilder
    renders: tuple[str, ...]


from tinyvm.generators import gen_counter, gen_register_trace


# ---- Tier 0 ----

def _tier0_train_axes(rng: _random.Random) -> dict[str, int | bool]:
    return {"n": rng.randint(4, 8)}


def _tier0_build(rng: _random.Random, axes: dict[str, int | bool]) -> Program:
    return gen_counter(n=axes["n"], rng=rng)


TIER0 = DatasetConfig(
    tier="tier0",
    train_size=100_000,
    train_axes=_tier0_train_axes,
    eval_buckets=(EvalBucket(name="all", size=10_000, fixed_axes={"n": 8}),),
    build=_tier0_build,
    renders=("direct",),
)


# ---- Tier 1 ----

def _tier1_train_axes(rng: _random.Random) -> dict[str, int | bool]:
    return {"n": rng.randint(8, 32), "k": rng.choice([2, 4, 8])}


def _tier1_build(rng: _random.Random, axes: dict[str, int | bool]) -> Program:
    return gen_register_trace(n=axes["n"], k=axes["k"], rng=rng)


TIER1 = DatasetConfig(
    tier="tier1",
    train_size=200_000,
    train_axes=_tier1_train_axes,
    eval_buckets=tuple(
        EvalBucket(name=f"len_{n}", size=20_000, fixed_axes={"n": n, "k": 4})
        for n in (8, 16, 32, 48, 64, 96, 128)
    ),
    build=_tier1_build,
    renders=("direct",),
)
