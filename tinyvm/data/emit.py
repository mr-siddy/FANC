"""Emit JSONL datasets to disk. Spec §7."""
from __future__ import annotations

import hashlib


def _row_seed(seed_base: int, split: str, bucket: str | None, index: int) -> int:
    """Derive a deterministic per-row seed. Collision-free across (split, bucket, index) triples."""
    key = f"{seed_base}|{split}|{bucket or ''}|{index}".encode()
    return int.from_bytes(hashlib.sha256(key).digest()[:8], "big")
