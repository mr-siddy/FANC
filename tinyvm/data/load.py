"""Streaming JSONL reader. Spec §8."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

from tinyvm.data.schema import Row, from_row


def load_jsonl(path: Path) -> Iterator[Row]:
    """Stream rows from a single .jsonl file as Row(program, trace, meta, renders) tuples."""
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            yield from_row(json.loads(line))


def load_split(
    dataset_dir: Path,
    split: str,
    bucket: str | None = None,
) -> Iterator[Row]:
    """Convenience: load all rows for a (split, bucket). Train: bucket=None."""
    dataset_dir = Path(dataset_dir)
    if split == "train":
        return load_jsonl(dataset_dir / "train.jsonl")
    if bucket is None:
        raise ValueError("bucket required for split='eval'")
    return load_jsonl(dataset_dir / "eval" / f"{bucket}.jsonl")


def load_prompts(path: Path, mode: str = "direct") -> Iterator[tuple[list[int], list[int]]]:
    """Fast path: stream just (input_ids, target_ids) for the chosen render mode.

    Skips reconstruction of Program/ExecutionTrace. Use this in DataLoader
    pipelines that don't need the IR.

    Raises KeyError if `mode` isn't present in a row's `renders` block.
    """
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            r = row["renders"][mode]
            yield r["input_ids"], r["target_ids"]


def load_manifest(dataset_dir: Path) -> dict:
    """Read manifest.json. Raises FileNotFoundError if missing — that means the emit was incomplete."""
    return json.loads((Path(dataset_dir) / "manifest.json").read_text(encoding="utf-8"))
