"""Find pedagogically good examples from the Tier 1 dataset.

Criteria for a "good" example:
  - Non-zero output (computation is observable; not the degenerate all-zeros case)
  - Multiple distinct opcodes used (mix, not just NEG/MOV)
  - Some register evolution visible in the trace (regs not all zero at end)
  - Compact enough to walk by hand (for short examples)
  - Demonstrates clamping or other interesting semantics where possible

Outputs JSON to docs/stats/examples.json with picked rows + walkthroughs.

Pickings:
  - 1 short train row (n ~ 10-16) — for the intro walkthrough
  - 1 eval_len_8 row (the trivial bucket, but a non-trivial example)
  - 1 eval_len_32 row (mid-size)
  - 1 eval_len_128 row (length-OOD; show only a slice of the trace)
  - 1 example showing arithmetic clamping (output near +/- 1023)
  - 1 example showing div-by-zero handling (a DIV with divisor=0 in the trace)
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path("data/tier1")
OUT = Path("docs/stats/examples.json")


def _row_signature(row: dict) -> dict:
    """Compute scoring signals for picking good examples."""
    program = row["program"]
    trace = row["trace"]
    op_set = {inst["op"] for inst in program}
    last_regs = trace["steps"][-1]["regs"] if trace["steps"] else []
    output = trace["output"]
    # Did any DIV instruction execute with divisor=0?
    # (Check by reading the regs before each DIV step.)
    div_by_zero_seen = False
    for i, inst in enumerate(program):
        if inst["op"] == "DIV":
            # Find the step at this pc.
            for s in trace["steps"]:
                if s["pc"] == i:
                    # The divisor is regs[args[2]] BEFORE this step.
                    # The trace records regs AFTER, so we need the previous step's regs.
                    pass
            # Approx check: see if any preceding step left regs[args[2]] == 0.
            pass
    # Did any register hit the clamp boundary?
    clamping_seen = False
    for s in trace["steps"]:
        for r in s["regs"]:
            if r in (1023, -1024):
                clamping_seen = True
                break
        if clamping_seen:
            break
    return {
        "n_opcodes": len(op_set),
        "output_nonzero": any(v != 0 for v in output),
        "last_regs_nonzero": any(r != 0 for r in last_regs),
        "output": output,
        "last_regs": last_regs,
        "clamping_seen": clamping_seen,
        "opcodes_used": sorted(op_set),
    }


def _walk_program(row: dict, max_steps_shown: int = 0) -> dict:
    """Build a structured walkthrough of a row."""
    program = row["program"]
    trace = row["trace"]
    annotated = []
    for i, inst in enumerate(program):
        # Find the step with this pc
        step_at_i = next((s for s in trace["steps"] if s["pc"] == i), None)
        annotated.append({
            "idx": i,
            "op": inst["op"],
            "args": inst["args"],
            "label": inst.get("label"),
            "target": inst.get("target"),
            "regs_after": step_at_i["regs"] if step_at_i else None,
            "emitted": step_at_i.get("emitted") if step_at_i else None,
        })
    return {
        "meta": row["meta"],
        "program_text": row["renders"]["direct"]["input_text"],
        "target_text": row["renders"]["direct"]["target_text"],
        "annotated": annotated,
        "trace_output": trace["output"],
        "halted": trace["halted"],
        "input_ids": row["renders"]["direct"]["input_ids"],
        "target_ids": row["renders"]["direct"]["target_ids"],
        "signature": _row_signature(row),
    }


def _scan(path: Path, max_scan: int = 5000):
    """Yield rows from a jsonl file, up to max_scan."""
    with path.open(encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= max_scan:
                break
            yield json.loads(line)


def _score(sig: dict) -> tuple:
    """Higher is better. Tuple sort: (output_nonzero, last_regs_nonzero, n_opcodes)."""
    return (
        int(sig["output_nonzero"]),
        int(sig["last_regs_nonzero"]),
        int(sig["clamping_seen"]),
        sig["n_opcodes"],
    )


def _pick_best(path: Path, max_scan: int, min_n_opcodes: int = 5):
    """Return the best row in the first max_scan rows of `path`."""
    best = None
    best_score = (-1, -1, -1, -1)
    for row in _scan(path, max_scan):
        sig = _row_signature(row)
        if sig["n_opcodes"] < min_n_opcodes:
            continue
        score = _score(sig)
        if score > best_score:
            best_score = score
            best = row
    return best


def main():
    print("Picking train example (short, varied, non-trivial output)...")
    # For train, we want a SHORT program (n ~ 10-14 body) for easy walkthrough.
    # Scan many train rows; pick one that's short, non-zero output, varied ops.
    best_train = None
    best_train_score = (-1, -1, -1, -1)
    for row in _scan(ROOT / "train.jsonl", max_scan=5000):
        n_body = row["meta"]["axes"]["n"]
        if not (10 <= n_body <= 14):
            continue
        sig = _row_signature(row)
        if sig["n_opcodes"] < 5:
            continue
        score = _score(sig)
        if score > best_train_score:
            best_train_score = score
            best_train = row
    if best_train is None:
        print("WARNING: no good train example found; relaxing constraints")
        best_train = next(_scan(ROOT / "train.jsonl", max_scan=10))

    print("Picking eval_len_8 example...")
    best_len8 = _pick_best(ROOT / "eval" / "len_8.jsonl", max_scan=2000, min_n_opcodes=4)
    print("Picking eval_len_32 example...")
    best_len32 = _pick_best(ROOT / "eval" / "len_32.jsonl", max_scan=2000, min_n_opcodes=6)
    print("Picking eval_len_128 example...")
    best_len128 = _pick_best(ROOT / "eval" / "len_128.jsonl", max_scan=500, min_n_opcodes=7)

    print("Looking for a clamping example...")
    clamping_ex = None
    for row in _scan(ROOT / "eval" / "len_32.jsonl", max_scan=2000):
        sig = _row_signature(row)
        if sig["clamping_seen"] and sig["output_nonzero"]:
            clamping_ex = row
            break

    print("Looking for a div-by-zero observable example...")
    # An interesting div-by-zero is when the divisor is 0 and the result still gets used.
    div0_ex = None
    for row in _scan(ROOT / "eval" / "len_16.jsonl", max_scan=2000):
        program = row["program"]
        trace = row["trace"]
        for i, inst in enumerate(program):
            if inst["op"] != "DIV":
                continue
            divisor_reg = inst["args"][2]
            # Find regs immediately before this step.
            prev_regs = None
            for j, s in enumerate(trace["steps"]):
                if s["pc"] == i:
                    if j == 0:
                        prev_regs = [0] * 8
                    else:
                        prev_regs = trace["steps"][j - 1]["regs"]
                    break
            if prev_regs is not None and prev_regs[divisor_reg] == 0:
                div0_ex = row
                break
        if div0_ex is not None:
            break

    examples = {
        "train_short": _walk_program(best_train),
        "eval_len_8":  _walk_program(best_len8),
        "eval_len_32": _walk_program(best_len32),
        "eval_len_128": _walk_program(best_len128),
    }
    if clamping_ex is not None:
        examples["clamping_demo"] = _walk_program(clamping_ex)
    if div0_ex is not None:
        examples["div_by_zero_demo"] = _walk_program(div0_ex)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(examples, indent=2))
    print(f"\n✓ Wrote {OUT}")
    print(f"  Examples picked: {list(examples.keys())}")
    for name, ex in examples.items():
        sig = ex["signature"]
        print(f"  [{name:18s}] axes={ex['meta']['axes']}  output={sig['output']}  "
              f"clamping={sig['clamping_seen']}  ops={len(sig['opcodes_used'])}")


if __name__ == "__main__":
    main()
