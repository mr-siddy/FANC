"""Streaming JSONL reader. Spec §8."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

from tinyvm.data.schema import Row, from_row


def load_jsonl(path: Path) -> Iterator[Row]:
    """Stream rows from a single .jsonl file as Row(program, trace, meta, renders) tuples."""
    with Path(path).open() as f:
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
