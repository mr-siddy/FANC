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
COUNTER_SEEDS: list[tuple[int, int]] = [
    (0, 4), (1, 8), (2, 4), (3, 6),
    (4, 12), (5, 16), (6, 24), (7, 8),
]

REGISTER_TRACE_SPECS: list[tuple[int, int, int]] = [  # (seed, n, k)
    (0, 8, 2), (1, 16, 4), (2, 32, 4), (3, 16, 8),
    (4, 48, 4), (5, 48, 6), (6, 64, 8),
    (7, 16, 2), (8, 24, 6), (9, 32, 8),
    (10, 48, 8), (11, 64, 4),
]

BRANCHED_SPECS: list[tuple[int, GenSpec]] = [
    (0, GenSpec(n=24, k=4, b=1, l=0)),
    (1, GenSpec(n=32, k=4, b=2, l=4)),
    (2, GenSpec(n=48, k=6, b=2, l=8)),
    (3, GenSpec(n=48, k=6, b=0, l=0, use_stack=True, stack_frames=2)),
    (4, GenSpec(n=48, k=4, b=2, l=4)),
    (5, GenSpec(n=64, k=6, b=4, l=8)),
    (6, GenSpec(n=96, k=6, b=4, l=12)),
    (7, GenSpec(n=128, k=8, b=8, l=16)),
    (8, GenSpec(n=32, k=4, b=1, l=0, use_stack=True, stack_frames=1)),
    (9, GenSpec(n=48, k=6, b=2, l=0, use_stack=True, stack_frames=2)),
    (10, GenSpec(n=64, k=6, b=4, l=0, use_stack=True, stack_frames=2)),
    (11, GenSpec(n=64, k=8, b=2, l=0, use_stack=True, stack_frames=3)),
    (12, GenSpec(n=48, k=4, b=0, l=4, use_stack=True, stack_frames=1)),
    (13, GenSpec(n=64, k=6, b=0, l=8, use_stack=True, stack_frames=2)),
    (14, GenSpec(n=96, k=8, b=0, l=12, use_stack=True, stack_frames=2)),
    (15, GenSpec(n=64, k=6, b=2, l=4, use_stack=True, stack_frames=1)),
    (16, GenSpec(n=96, k=6, b=2, l=8, use_stack=True, stack_frames=2)),
    (17, GenSpec(n=128, k=8, b=4, l=8, use_stack=True, stack_frames=2)),
    (18, GenSpec(n=128, k=8, b=4, l=12, use_stack=True, stack_frames=3)),
    (19, GenSpec(n=24, k=4, b=3, l=2)),
    (20, GenSpec(n=24, k=4, b=0, l=6)),
    (21, GenSpec(n=32, k=4, b=0, l=8)),
    (22, GenSpec(n=48, k=6, b=1, l=2)),
    (23, GenSpec(n=64, k=8, b=2, l=6)),
    (24, GenSpec(n=80, k=8, b=4, l=4)),
    (25, GenSpec(n=80, k=8, b=2, l=12)),
    (26, GenSpec(n=96, k=6, b=4, l=6)),
    (27, GenSpec(n=64, k=6, b=1, l=16)),
    (28, GenSpec(n=48, k=4, b=4, l=2)),
    (29, GenSpec(n=64, k=4, b=2, l=4, use_stack=True, stack_frames=1)),
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
