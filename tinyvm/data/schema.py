"""JSONL row schema for tinyvm.data: dataclasses + (de)serialisation.

Spec §5.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple

from tinyvm.isa import Program, Instruction
from tinyvm.interpreter import ExecutionTrace, StepRecord


@dataclass(frozen=True)
class RenderedPrompt:
    """One render mode's pre-computed prompt (both token IDs and surface text)."""
    input_ids: list[int]
    target_ids: list[int]
    input_text: str
    target_text: str


@dataclass(frozen=True)
class RowMeta:
    """Per-row metadata. Lightweight; held outside the heavier IR + renders blocks."""
    tier: str                          # "tier0" | "tier1" | "tier2"
    split: str                         # "train" | "eval"
    bucket: str | None                 # eval bucket name; None for train
    seed: int                          # row-specific seed used to derive the program
    axes: dict[str, int | bool]        # axis dial values at generation time
    renders: tuple[str, ...]           # render modes populated in this row


class Row(NamedTuple):
    """A loaded JSONL row: deserialised IR + metadata + populated renders."""
    program: Program
    trace: ExecutionTrace
    meta: RowMeta
    renders: dict[str, RenderedPrompt]


def _instruction_to_dict(inst: Instruction) -> dict:
    return {
        "op": inst.op.name,
        "args": list(inst.args),
        "label": inst.label,
        "target": inst.target,
    }


def _step_to_dict(step: StepRecord) -> dict:
    return {
        "pc": step.pc,
        "regs": list(step.regs),
        "stack": list(step.stack),
        "emitted": step.emitted,
    }


def _rendered_prompt_to_dict(rp: RenderedPrompt) -> dict:
    return {
        "input_ids": list(rp.input_ids),
        "target_ids": list(rp.target_ids),
        "input_text": rp.input_text,
        "target_text": rp.target_text,
    }


def to_row(
    program: Program,
    trace: ExecutionTrace,
    meta: RowMeta,
    renders: dict[str, RenderedPrompt],
) -> dict:
    """Serialise to a JSON-able dict. Pure function; no I/O."""
    return {
        "meta": {
            "tier": meta.tier,
            "split": meta.split,
            "bucket": meta.bucket,
            "seed": meta.seed,
            "axes": dict(meta.axes),
            "renders": list(meta.renders),
        },
        "program": [_instruction_to_dict(inst) for inst in program.instructions],
        "trace": {
            "steps": [_step_to_dict(s) for s in trace.steps],
            "output": list(trace.output),
            "halted": trace.halted,
        },
        "renders": {name: _rendered_prompt_to_dict(rp) for name, rp in renders.items()},
    }
