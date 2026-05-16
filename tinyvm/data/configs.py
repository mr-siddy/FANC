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
