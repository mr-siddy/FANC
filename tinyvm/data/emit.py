"""Emit JSONL datasets to disk. Spec §7."""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Callable

from tinyvm import tokeniser
from tinyvm.data.configs import DatasetConfig, EvalBucket
from tinyvm.data.schema import RenderedPrompt, RowMeta, to_row
from tinyvm.interpreter import ExecutionTrace, run
from tinyvm.isa import Program


def _row_seed(seed_base: int, split: str, bucket: str | None, index: int) -> int:
    """Derive a deterministic per-row seed. Collision-free across (split, bucket, index) triples."""
    key = f"{seed_base}|{split}|{bucket or ''}|{index}".encode()
    return int.from_bytes(hashlib.sha256(key).digest()[:8], "big")


_ID_RENDERERS: dict[str, Callable[[Program, ExecutionTrace], tuple[list[int], list[int]]]] = {
    "direct": tokeniser.render_direct,
    "cot": tokeniser.render_cot,
}

_TEXT_RENDERERS: dict[str, Callable[[Program, ExecutionTrace], tuple[str, str]]] = {
    "direct": tokeniser.render_direct_text,
    "cot": tokeniser.render_cot_text,
}


def _build_renders(
    program: Program,
    trace: ExecutionTrace,
    modes: tuple[str, ...],
) -> dict[str, RenderedPrompt]:
    """Render `program` + `trace` under each requested mode. Raises KeyError on unknown mode."""
    out: dict[str, RenderedPrompt] = {}
    for m in modes:
        input_ids, target_ids = _ID_RENDERERS[m](program, trace)
        input_text, target_text = _TEXT_RENDERERS[m](program, trace)
        out[m] = RenderedPrompt(
            input_ids=input_ids,
            target_ids=target_ids,
            input_text=input_text,
            target_text=target_text,
        )
    return out


def _emit_split(
    config: DatasetConfig,
    out_path: Path,
    split: str,
    bucket: EvalBucket | None,
    n_rows: int,
    seed_base: int,
) -> tuple[int, str]:
    """Stream-write one .jsonl file. Returns (row_count, sha256_hexdigest).

    File is written incrementally; on any exception the partial file is left in place
    and the SHA reflects nothing — caller decides whether to clean up.
    """
    sha = hashlib.sha256()
    bucket_name = bucket.name if bucket is not None else None
    written = 0
    with out_path.open("w") as f:
        for i in range(n_rows):
            row_seed = _row_seed(seed_base, split, bucket_name, i)
            rng = random.Random(row_seed)
            if split == "train":
                axes = config.train_axes(rng)
            else:
                axes = dict(bucket.fixed_axes)
            program = config.build(rng, axes)
            trace = run(program)
            renders = _build_renders(program, trace, config.renders)
            meta = RowMeta(
                tier=config.tier,
                split=split,
                bucket=bucket_name,
                seed=row_seed,
                axes=axes,
                renders=config.renders,
            )
            row_dict = to_row(program, trace, meta, renders)
            line = json.dumps(row_dict, separators=(",", ":")) + "\n"
            f.write(line)
            sha.update(line.encode())
            written += 1
    return written, sha.hexdigest()
