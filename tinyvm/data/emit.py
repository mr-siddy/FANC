"""Emit JSONL datasets to disk. Spec §7."""
from __future__ import annotations

import hashlib
from typing import Callable

from tinyvm import tokeniser
from tinyvm.data.schema import RenderedPrompt
from tinyvm.interpreter import ExecutionTrace
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
