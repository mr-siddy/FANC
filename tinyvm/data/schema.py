"""JSONL row schema for tinyvm.data: dataclasses + (de)serialisation.

Spec §5.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RenderedPrompt:
    """One render mode's pre-computed prompt (both token IDs and surface text)."""
    input_ids: list[int]
    target_ids: list[int]
    input_text: str
    target_text: str


@dataclass(frozen=True)
class RowMeta:
    """Per-row metadata. Lightweight; held outside the heavier IR + renders blocks."""
    tier: str                          # "tier0" | "tier1" | "tier2"
    split: str                         # "train" | "eval"
    bucket: str | None                 # eval bucket name; None for train
    seed: int                          # row-specific seed used to derive the program
    axes: dict[str, int | bool]        # axis dial values at generation time
    renders: tuple[str, ...]           # render modes populated in this row
