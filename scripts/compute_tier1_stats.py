"""Compute Tier 1 dataset statistics for the documentation.

Outputs JSON to docs/stats/tier1_stats.json with:
  - per-bucket row counts, byte sizes, SHA prefixes
  - op frequency (across all train + eval rows)
  - program length distribution (histograms per bucket)
  - trace step count, output stream length distributions
  - token sequence length distributions (input/target) per bucket
  - register usage patterns (which registers are written/read)

Train is sampled (20K rows) for speed; eval splits are exhaustive (each is 20K).
"""
from __future__ import annotations

import json
import random
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("data/tier1")
OUT = Path("docs/stats/tier1_stats.json")
SAMPLE_PER_SPLIT = 20_000  # eval buckets are exactly this size; for train we read first N


def _iter_jsonl(path: Path, limit: int | None = None):
    with path.open(encoding="utf-8") as f:
        for i, line in enumerate(f):
            if limit is not None and i >= limit:
                break
            yield json.loads(line)


def _analyse_split(name: str, path: Path, limit: int | None = None) -> dict:
    print(f"[{name}] analysing {path} (limit={limit}) ...", flush=True)
    t0 = time.time()
    op_freq: Counter[str] = Counter()
    prog_lens: list[int] = []
    trace_step_counts: list[int] = []
    output_lens: list[int] = []
    input_id_lens: list[int] = []
    target_id_lens: list[int] = []
    input_text_lens: list[int] = []  # in chars
    target_text_lens: list[int] = []
    register_writes: Counter[int] = Counter()
    n = 0
    for row in _iter_jsonl(path, limit=limit):
        n += 1
        instructions = row["program"]
        prog_lens.append(len(instructions))
        for inst in instructions:
            op_freq[inst["op"]] += 1
            # Track register writes (first arg for arithmetic / load / mov / pop)
            args = inst["args"]
            op = inst["op"]
            if op in {"LOAD", "MOV", "ADD", "SUB", "MUL", "DIV", "NEG", "EQ", "LT", "POP"} and args:
                register_writes[args[0]] += 1
        steps = row["trace"]["steps"]
        trace_step_counts.append(len(steps))
        output_lens.append(len(row["trace"]["output"]))
        d = row["renders"]["direct"]
        input_id_lens.append(len(d["input_ids"]))
        target_id_lens.append(len(d["target_ids"]))
        input_text_lens.append(len(d["input_text"]))
        target_text_lens.append(len(d["target_text"]))
    elapsed = time.time() - t0
    print(f"[{name}] {n} rows in {elapsed:.1f}s", flush=True)

    def _summary(xs: list[int]) -> dict:
        if not xs:
            return {}
        xs_sorted = sorted(xs)
        n_x = len(xs_sorted)
        return {
            "n": n_x,
            "min": xs_sorted[0],
            "p25": xs_sorted[n_x // 4],
            "p50": xs_sorted[n_x // 2],
            "p75": xs_sorted[(3 * n_x) // 4],
            "p95": xs_sorted[min(n_x - 1, int(0.95 * n_x))],
            "p99": xs_sorted[min(n_x - 1, int(0.99 * n_x))],
            "max": xs_sorted[-1],
            "mean": sum(xs_sorted) / n_x,
        }

    return {
        "name": name,
        "rows_analysed": n,
        "elapsed_s": round(elapsed, 2),
        "op_freq": dict(op_freq.most_common()),
        "program_length": _summary(prog_lens),
        "trace_steps": _summary(trace_step_counts),
        "output_len": _summary(output_lens),
        "input_id_len": _summary(input_id_lens),
        "target_id_len": _summary(target_id_lens),
        "input_text_chars": _summary(input_text_lens),
        "target_text_chars": _summary(target_text_lens),
        "register_writes": dict(sorted(register_writes.items())),
        # Raw arrays for histograms (cap at 10K to keep file size reasonable):
        "input_id_len_raw": input_id_lens[:10_000],
        "target_id_len_raw": target_id_lens[:10_000],
        "program_length_raw": prog_lens[:10_000],
    }


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))

    splits = {}
    # Train — sample
    splits["train"] = _analyse_split("train", ROOT / "train.jsonl", limit=SAMPLE_PER_SPLIT)
    # Eval buckets — exhaustive
    for bucket_path in sorted((ROOT / "eval").glob("*.jsonl")):
        name = f"eval_{bucket_path.stem}"
        splits[name] = _analyse_split(name, bucket_path, limit=None)

    # Aggregate op freq across all splits.
    all_ops: Counter[str] = Counter()
    for s in splits.values():
        all_ops.update(s["op_freq"])

    out_doc = {
        "manifest": manifest,
        "splits": splits,
        "aggregate_op_freq": dict(all_ops.most_common()),
        "train_sample_size": SAMPLE_PER_SPLIT,
    }
    OUT.write_text(json.dumps(out_doc, indent=2))
    print(f"\n✓ Wrote {OUT}")
    print(f"  total ops counted: {sum(all_ops.values()):,}")
    print(f"  rows analysed: {sum(s['rows_analysed'] for s in splits.values()):,}")


if __name__ == "__main__":
    main()
