"""Emit JSONL datasets to disk. Spec §7."""
from __future__ import annotations

import hashlib
import json
import random
import subprocess
from datetime import datetime, timezone
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
    with out_path.open("w", encoding="utf-8") as f:
        for i in range(n_rows):
            row_seed = _row_seed(seed_base, split, bucket_name, i)
            rng = random.Random(row_seed)
            if split == "train":
                axes = config.train_axes(rng)
            elif split == "eval":
                assert bucket is not None, "eval split requires a bucket"
                axes = dict(bucket.fixed_axes)
            else:
                raise ValueError(f"unknown split {split!r}")
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
            sha.update(line.encode("utf-8"))
            written += 1
    return written, sha.hexdigest()


def _read_tinyvm_version() -> str:
    """Best-effort version string. Falls back to '0.0.0+unknown' if discovery fails."""
    try:
        from importlib.metadata import version
        return version("tinyvm")
    except Exception:
        return "0.0.0+unknown"


def _read_git_commit() -> str:
    """Best-effort short git SHA of HEAD. Falls back to 'unknown' if not in a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True, timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def emit(config: DatasetConfig, out_dir: Path, seed_base: int = 0) -> Path:
    """Emit a full dataset to out_dir/<config.tier>/. Returns the path to manifest.json.

    Layout produced:
      out_dir/<tier>/
        train.jsonl
        eval/<bucket_name>.jsonl       (one per config.eval_buckets entry)
        manifest.json                  (written LAST; its presence means emit completed)
    """
    out_dir = Path(out_dir)
    tier_dir = out_dir / config.tier
    (tier_dir / "eval").mkdir(parents=True, exist_ok=True)

    files: dict[str, dict] = {}

    # Train.
    train_path = tier_dir / "train.jsonl"
    n, h = _emit_split(config, train_path, "train", None, config.train_size, seed_base)
    files["train.jsonl"] = {"rows": n, "sha256": h}

    # Eval buckets.
    for bucket in config.eval_buckets:
        path = tier_dir / "eval" / f"{bucket.name}.jsonl"
        n, h = _emit_split(config, path, "eval", bucket, bucket.size, seed_base)
        files[f"eval/{bucket.name}.jsonl"] = {"rows": n, "sha256": h}

    # Manifest written last — its presence indicates emit completed.
    manifest_path = tier_dir / "manifest.json"
    manifest = {
        "tier": config.tier,
        "seed_base": seed_base,
        "tinyvm_version": _read_tinyvm_version(),
        "tinyvm_commit": _read_git_commit(),
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "files": files,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path
