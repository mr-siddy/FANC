"""Emit a ComparisonBundle JSON consumable by tinyvm-viz Compare page."""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from tinyvm.generators import gen_branched, gen_counter, gen_register_trace, GenSpec
from tinyvm.interpreter import run
from tinyvm.tokeniser import render_direct_text


def _trace_to_json(trace: Any) -> dict:
    return {
        "steps": [
            {"pc": s.pc, "regs": list(s.regs), "stack": list(s.stack), "emitted": s.emitted}
            for s in trace.steps
        ],
        "output": list(trace.output),
        "halted": trace.halted,
    }


def build_bundle(generator: str, seed: int, generator_kwargs: dict, prediction_output: list[int]) -> dict:
    rng = random.Random(seed)
    if generator == "gen_counter":
        p = gen_counter(rng=rng, **generator_kwargs)
    elif generator == "gen_register_trace":
        p = gen_register_trace(rng=rng, **generator_kwargs)
    elif generator == "gen_branched":
        spec = GenSpec(**generator_kwargs)
        p = gen_branched(spec=spec, rng=rng)
    else:
        raise ValueError(f"unknown generator: {generator}")
    trace = run(p)
    source, _ = render_direct_text(p, trace)
    return {
        "schema": "tinyvm-viz/comparison/v1",
        "meta": {"generator": generator, "seed": seed, "spec": generator_kwargs},
        "source": source,
        "groundTruth": {"trace": _trace_to_json(trace)},
        "prediction": {"output": list(prediction_output)},
    }


def write_bundle(path: Path, *, generator: str, seed: int, generator_kwargs: dict, prediction_output: list[int]) -> None:
    b = build_bundle(generator, seed, generator_kwargs, prediction_output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(b, indent=2, sort_keys=True))
