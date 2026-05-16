"""Emit golden parity fixtures consumed by the TS interpreter."""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from tinyvm.generators import gen_branched, gen_counter, gen_register_trace, GenSpec
from tinyvm.interpreter import run
from tinyvm.isa import Program
from tinyvm.tokeniser import render_direct_text


# A small, fixed sweep — Tier 0/1/2 difficulty axes.
COUNTER_SEEDS: list[tuple[int, int]] = [(0, 4), (1, 8), (2, 4), (3, 6)]
REGISTER_TRACE_SPECS: list[tuple[int, int, int]] = [  # (seed, n, k)
    (0, 8, 2), (1, 16, 4), (2, 32, 4), (3, 16, 8),
]
BRANCHED_SPECS: list[tuple[int, GenSpec]] = [
    (0, GenSpec(n=24, k=4, b=1, l=0)),
    (1, GenSpec(n=32, k=4, b=2, l=4)),
    (2, GenSpec(n=48, k=6, b=2, l=8)),
    (3, GenSpec(n=48, k=6, b=0, l=0, use_stack=True, stack_frames=2)),
]


def _serialise_inst(inst: Any) -> dict:
    return {
        "op": int(inst.op),
        "args": list(inst.args),
        "label": inst.label,
        "target": inst.target,
    }


def _serialise_program(p: Program) -> dict:
    return {
        "instructions": [_serialise_inst(i) for i in p.instructions],
        "label_index": dict(p.label_index),
    }


def _serialise_trace(t: Any) -> dict:
    return {
        "steps": [
            {"pc": s.pc, "regs": list(s.regs), "stack": list(s.stack), "emitted": s.emitted}
            for s in t.steps
        ],
        "output": list(t.output),
        "halted": t.halted,
    }


def _one(generator: str, seed: int, spec: dict, program: Program) -> dict:
    trace = run(program)
    src, _ = render_direct_text(program, trace)
    return {
        "seed": seed,
        "generator": generator,
        "spec": spec,
        "source_text": src,
        "program_ir": _serialise_program(program),
        "expected_trace": _serialise_trace(trace),
    }


def build_fixtures() -> list[dict]:
    out: list[dict] = []
    for seed, n in COUNTER_SEEDS:
        p = gen_counter(n=n, rng=random.Random(seed))
        out.append(_one("gen_counter", seed, {"n": n}, p))
    for seed, n, k in REGISTER_TRACE_SPECS:
        p = gen_register_trace(n=n, k=k, rng=random.Random(seed))
        out.append(_one("gen_register_trace", seed, {"n": n, "k": k}, p))
    for seed, spec in BRANCHED_SPECS:
        p = gen_branched(spec=spec, rng=random.Random(seed))
        out.append(_one(
            "gen_branched",
            seed,
            {"n": spec.n, "k": spec.k, "b": spec.b, "l": spec.l, "use_stack": spec.use_stack, "stack_frames": spec.stack_frames},
            p,
        ))
    return out


def write_fixtures(out_path: Path) -> None:
    fixtures = build_fixtures()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(fixtures, indent=2, sort_keys=True))


if __name__ == "__main__":
    target = Path(__file__).resolve().parents[2] / "tinyvm-viz" / "tests" / "fixtures" / "golden.json"
    write_fixtures(target)
    print(f"wrote {target}")
