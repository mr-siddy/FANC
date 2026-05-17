# Tiny-VM Data Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `tinyvm/data/` sub-package — materialise the per-tier datasets to disk as JSONL files at the sizes specified in `Latent_State_as_Computer.docx` §11.2, with rich-IR rows that also carry pre-rendered training prompts. Day 3 of the FANC experimental program.

**Architecture:** Five focused files under `tinyvm/data/`. `schema.py` owns the JSON row layout (serialise/deserialise). `configs.py` is data-only — `DatasetConfig` literals for `TIER0`, `TIER1`, `TIER2`. `emit.py` writes the JSONL files plus a manifest with per-file SHA-256. `load.py` is the inverse — streaming reader with a fast `load_prompts` path for training. `__main__.py` is a thin argparse CLI. The pipeline is single-process, Python-only, deterministic via SHA-256-derived per-row seeds.

**Tech Stack:** Python 3.10+, stdlib only (`json`, `hashlib`, `random`, `pathlib`, `argparse`, `dataclasses`, `datetime`), pytest. No new dependencies beyond what PR #1 already brings in.

---

## File structure

```
FANC/
├── pyproject.toml                      # MODIFY (Task 1) — register data sub-package
├── tinyvm/
│   ├── __init__.py                     # untouched
│   ├── isa.py                          # untouched
│   ├── interpreter.py                  # untouched
│   ├── tokeniser.py                    # untouched
│   ├── verifier.py                     # untouched
│   ├── generators.py                   # untouched
│   └── data/                           # NEW sub-package
│       ├── __init__.py                 # CREATE (Task 1)
│       ├── schema.py                   # CREATE (Tasks 2–5)
│       ├── configs.py                  # CREATE (Tasks 6–8)
│       ├── emit.py                     # CREATE (Tasks 9–12)
│       ├── load.py                     # CREATE (Tasks 13–14)
│       ├── __main__.py                 # CREATE (Tasks 15–16)
│       └── tests/
│           ├── __init__.py             # CREATE (Task 1)
│           ├── test_schema.py          # CREATE (Tasks 2–5)
│           ├── test_configs.py         # CREATE (Tasks 6–8)
│           ├── test_emit.py            # CREATE (Tasks 9–12)
│           ├── test_load.py            # CREATE (Tasks 13–14)
│           └── test_pipeline.py        # CREATE (Tasks 17–18)
```

**File-by-file responsibility:**

- `schema.py` — `RowMeta`, `RenderedPrompt`, `Row` dataclasses + `to_row` / `from_row` pure functions.
- `configs.py` — `EvalBucket`, `DatasetConfig` dataclasses + `TIER0`, `TIER1`, `TIER2` instances + `CONFIGS` dict.
- `emit.py` — `emit(config, out_dir, seed_base)` public function + private helpers (`_row_seed`, `_build_renders`, `_emit_split`).
- `load.py` — `load_jsonl`, `load_split`, `load_prompts`, `load_manifest`.
- `__main__.py` — argparse CLI with `emit` and `verify` subcommands.

---

## Phase A — Scaffolding

### Task 1: Sub-package scaffolding

**Files:**
- Create: `tinyvm/data/__init__.py`
- Create: `tinyvm/data/tests/__init__.py`
- Modify: `pyproject.toml` (ensure `find:` picks up the new sub-package — should be automatic via `tinyvm*` glob, verify only)

- [ ] **Step 1: Create `tinyvm/data/__init__.py`**

```python
"""Tiny-VM data pipeline: materialise per-tier datasets to JSONL on disk.

See docs/superpowers/specs/2026-05-16-tinyvm-data-pipeline-design.md.
"""
```

- [ ] **Step 2: Create `tinyvm/data/tests/__init__.py`** (empty file)

```python
```

- [ ] **Step 3: Verify pyproject.toml's package discovery picks up the new sub-package**

Run:
```bash
cd /Users/sidgraph/FANC && pip install -e . --no-deps 2>&1 | grep -i "tinyvm"
```

Expected: output contains `tinyvm.data` (the glob `tinyvm*` in `[tool.setuptools.packages.find]` should match).

If it doesn't, edit `pyproject.toml`'s `[tool.setuptools.packages.find]` block to include `"tinyvm.data*"` explicitly. Otherwise no pyproject changes are required.

- [ ] **Step 4: Confirm pytest discovers the new test directory**

Run: `cd /Users/sidgraph/FANC && pytest --collect-only tinyvm/data/tests/ 2>&1 | tail -5`

Expected: `no tests ran in 0.00s` (no tests yet) — exit code 5 is acceptable.

- [ ] **Step 5: Commit**

```bash
git -C /Users/sidgraph/FANC add tinyvm/data/__init__.py tinyvm/data/tests/__init__.py
# If pyproject.toml needed editing, include it:
# git -C /Users/sidgraph/FANC add pyproject.toml
git -C /Users/sidgraph/FANC commit -m "feat(tinyvm.data): scaffold data sub-package"
```

---

## Phase B — Schema

### Task 2: `RenderedPrompt` and `RowMeta` dataclasses

**Files:**
- Create: `tinyvm/data/schema.py`
- Create: `tinyvm/data/tests/test_schema.py`

Refs spec §5.2.

- [ ] **Step 1: Write the failing tests**

```python
# tinyvm/data/tests/test_schema.py
import pytest

from tinyvm.data.schema import RowMeta, RenderedPrompt


def test_rendered_prompt_is_frozen():
    rp = RenderedPrompt(input_ids=[1, 2], target_ids=[3], input_text="hi", target_text="bye")
    with pytest.raises((AttributeError, TypeError)):
        rp.input_ids = [99]  # type: ignore[misc]


def test_rendered_prompt_holds_four_fields():
    rp = RenderedPrompt(
        input_ids=[0, 47, 1],
        target_ids=[0, 39, 1],
        input_text="LOAD R0 5",
        target_text="5",
    )
    assert rp.input_ids == [0, 47, 1]
    assert rp.target_ids == [0, 39, 1]
    assert rp.input_text == "LOAD R0 5"
    assert rp.target_text == "5"


def test_row_meta_is_frozen():
    meta = RowMeta(
        tier="tier1", split="train", bucket=None, seed=42,
        axes={"n": 16, "k": 4}, renders=("direct",),
    )
    with pytest.raises((AttributeError, TypeError)):
        meta.tier = "tier2"  # type: ignore[misc]


def test_row_meta_renders_is_tuple():
    meta = RowMeta(
        tier="tier2", split="train", bucket=None, seed=0,
        axes={}, renders=("direct", "cot"),
    )
    assert meta.renders == ("direct", "cot")
    assert isinstance(meta.renders, tuple)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/test_schema.py -v`
Expected: `ModuleNotFoundError: tinyvm.data.schema`.

- [ ] **Step 3: Write `tinyvm/data/schema.py` with the two dataclasses**

```python
"""JSONL row schema for tinyvm.data: dataclasses + (de)serialisation.

Spec §5.
"""
from __future__ import annotations

from dataclasses import dataclass


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/test_schema.py -v`
Expected: all 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git -C /Users/sidgraph/FANC add tinyvm/data/schema.py tinyvm/data/tests/test_schema.py
git -C /Users/sidgraph/FANC commit -m "feat(tinyvm.data): RenderedPrompt and RowMeta dataclasses"
```

---

### Task 3: `Row` NamedTuple

**Files:**
- Modify: `tinyvm/data/schema.py`
- Modify: `tinyvm/data/tests/test_schema.py`

Refs spec §5.2.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/data/tests/test_schema.py
from tinyvm.data.schema import Row
from tinyvm.isa import Op, Instruction, Program
from tinyvm.interpreter import ExecutionTrace, StepRecord


def test_row_namedtuple_has_four_fields():
    p = Program.build((Instruction(Op.HALT),))
    trace = ExecutionTrace(steps=[], output=[], halted=True)
    meta = RowMeta(tier="tier0", split="train", bucket=None, seed=0,
                   axes={}, renders=("direct",))
    rp = RenderedPrompt(input_ids=[], target_ids=[], input_text="", target_text="")
    row = Row(program=p, trace=trace, meta=meta, renders={"direct": rp})
    assert row.program is p
    assert row.trace is trace
    assert row.meta is meta
    assert row.renders == {"direct": rp}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/test_schema.py -v`
Expected: `ImportError: cannot import name 'Row'`.

- [ ] **Step 3: Append `Row` to schema.py**

```python
# Append to tinyvm/data/schema.py
from typing import NamedTuple

from tinyvm.isa import Program
from tinyvm.interpreter import ExecutionTrace


class Row(NamedTuple):
    """A loaded JSONL row: deserialised IR + metadata + populated renders."""
    program: Program
    trace: ExecutionTrace
    meta: RowMeta
    renders: dict[str, RenderedPrompt]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/test_schema.py -v`
Expected: 5 passing.

- [ ] **Step 5: Commit**

```bash
git -C /Users/sidgraph/FANC add tinyvm/data/schema.py tinyvm/data/tests/test_schema.py
git -C /Users/sidgraph/FANC commit -m "feat(tinyvm.data): Row NamedTuple"
```

---

### Task 4: `to_row` serialiser

**Files:**
- Modify: `tinyvm/data/schema.py`
- Modify: `tinyvm/data/tests/test_schema.py`

Refs spec §5.1, §5.2.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/data/tests/test_schema.py
from tinyvm.data.schema import to_row


def test_to_row_serialises_meta_program_trace_renders():
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 5)),
        Instruction(Op.PRINT, args=(0,)),
        Instruction(Op.HALT),
    ))
    trace = ExecutionTrace(
        steps=[
            StepRecord(pc=0, regs=(5, 0, 0, 0, 0, 0, 0, 0), stack=(), emitted=None),
            StepRecord(pc=1, regs=(5, 0, 0, 0, 0, 0, 0, 0), stack=(), emitted=5),
            StepRecord(pc=2, regs=(5, 0, 0, 0, 0, 0, 0, 0), stack=(), emitted=None),
        ],
        output=[5],
        halted=True,
    )
    meta = RowMeta(tier="tier0", split="train", bucket=None, seed=42,
                   axes={"n": 3}, renders=("direct",))
    rp = RenderedPrompt(
        input_ids=[0, 47, 1, 5, 13, 1, 15, 56],
        target_ids=[0, 39, 1, 56],
        input_text="LOAD R0 5\nPRINT R0\nHALT",
        target_text="5",
    )
    out = to_row(p, trace, meta, {"direct": rp})
    # Top-level keys.
    assert set(out.keys()) == {"meta", "program", "trace", "renders"}
    # Meta.
    assert out["meta"]["tier"] == "tier0"
    assert out["meta"]["seed"] == 42
    assert out["meta"]["renders"] == ["direct"]      # tuple -> list under json
    # Program: list of instruction dicts; Op serialised by name.
    assert out["program"][0] == {"op": "LOAD", "args": [0, 5], "label": None, "target": None}
    assert out["program"][2] == {"op": "HALT", "args": [], "label": None, "target": None}
    # Trace: per-step record + output + halted.
    assert out["trace"]["output"] == [5]
    assert out["trace"]["halted"] is True
    assert out["trace"]["steps"][1] == {
        "pc": 1, "regs": [5, 0, 0, 0, 0, 0, 0, 0], "stack": [], "emitted": 5,
    }
    # Renders.
    assert out["renders"]["direct"]["input_text"] == "LOAD R0 5\nPRINT R0\nHALT"


def test_to_row_output_is_json_serialisable():
    import json
    p = Program.build((Instruction(Op.HALT),))
    trace = ExecutionTrace(steps=[
        StepRecord(pc=0, regs=(0,) * 8, stack=(), emitted=None),
    ], output=[], halted=True)
    meta = RowMeta(tier="tier0", split="train", bucket=None, seed=0,
                   axes={}, renders=())
    out = to_row(p, trace, meta, {})
    # json.dumps must not raise.
    s = json.dumps(out)
    assert isinstance(s, str)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/test_schema.py -v`
Expected: `ImportError: cannot import name 'to_row'`.

- [ ] **Step 3: Append `to_row` to schema.py**

```python
# Append to tinyvm/data/schema.py
from tinyvm.isa import Instruction
from tinyvm.interpreter import StepRecord


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/test_schema.py -v`
Expected: 7 passing.

- [ ] **Step 5: Commit**

```bash
git -C /Users/sidgraph/FANC add tinyvm/data/schema.py tinyvm/data/tests/test_schema.py
git -C /Users/sidgraph/FANC commit -m "feat(tinyvm.data): to_row serialiser"
```

---

### Task 5: `from_row` deserialiser + round-trip

**Files:**
- Modify: `tinyvm/data/schema.py`
- Modify: `tinyvm/data/tests/test_schema.py`

Refs spec §5.2, §5.3.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/data/tests/test_schema.py
import random
from tinyvm.data.schema import from_row


def test_from_row_inverts_to_row_on_simple_case():
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 5)),
        Instruction(Op.HALT),
    ))
    trace = ExecutionTrace(steps=[
        StepRecord(pc=0, regs=(5,) + (0,) * 7, stack=(), emitted=None),
        StepRecord(pc=1, regs=(5,) + (0,) * 7, stack=(), emitted=None),
    ], output=[], halted=True)
    meta = RowMeta(tier="tier0", split="train", bucket=None, seed=0,
                   axes={"n": 2}, renders=("direct",))
    rp = RenderedPrompt(input_ids=[1, 2], target_ids=[3], input_text="x", target_text="y")

    out = to_row(p, trace, meta, {"direct": rp})
    recovered = from_row(out)

    assert recovered.program == p
    assert recovered.trace.output == trace.output
    assert recovered.trace.steps == trace.steps
    assert recovered.trace.halted == trace.halted
    assert recovered.meta == meta
    assert recovered.renders == {"direct": rp}


def test_from_row_handles_labels_and_jumps():
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 0), label="ENTRY"),
        Instruction(Op.JZ, args=(0,), target="ENTRY"),
        Instruction(Op.HALT),
    ))
    trace = ExecutionTrace(steps=[
        StepRecord(pc=0, regs=(0,) * 8, stack=(), emitted=None),
    ], output=[], halted=True)
    meta = RowMeta(tier="tier1", split="eval", bucket="len_8", seed=99,
                   axes={"n": 3, "k": 1}, renders=())
    out = to_row(p, trace, meta, {})
    recovered = from_row(out)
    assert recovered.program == p
    assert recovered.program.instructions[0].label == "ENTRY"
    assert recovered.program.instructions[1].target == "ENTRY"


def test_round_trip_on_generated_programs():
    """Round-trip property: from_row(to_row(...)) reconstructs everything bit-exactly."""
    from tinyvm.generators import gen_register_trace, gen_counter
    from tinyvm.interpreter import run

    cases = []
    for seed in range(20):
        for gen in [
            lambda s: gen_counter(n=6, rng=random.Random(s)),
            lambda s: gen_register_trace(n=12, k=3, rng=random.Random(s)),
        ]:
            p = gen(seed)
            trace = run(p)
            cases.append(p)

    for p in cases:
        trace = run(p)
        meta = RowMeta(tier="tier0", split="train", bucket=None, seed=0,
                       axes={}, renders=())
        out = to_row(p, trace, meta, {})
        recovered = from_row(out)
        assert recovered.program == p
        assert recovered.trace.steps == trace.steps
        assert recovered.trace.output == trace.output
        assert recovered.trace.halted == trace.halted
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/test_schema.py -v`
Expected: `ImportError: cannot import name 'from_row'`.

- [ ] **Step 3: Append `from_row` to schema.py**

```python
# Append to tinyvm/data/schema.py
from tinyvm.isa import Op


def _instruction_from_dict(d: dict) -> Instruction:
    return Instruction(
        op=Op[d["op"]],
        args=tuple(d["args"]),
        label=d["label"],
        target=d["target"],
    )


def _step_from_dict(d: dict) -> StepRecord:
    return StepRecord(
        pc=d["pc"],
        regs=tuple(d["regs"]),
        stack=tuple(d["stack"]),
        emitted=d["emitted"],
    )


def _rendered_prompt_from_dict(d: dict) -> RenderedPrompt:
    return RenderedPrompt(
        input_ids=list(d["input_ids"]),
        target_ids=list(d["target_ids"]),
        input_text=d["input_text"],
        target_text=d["target_text"],
    )


def from_row(row: dict) -> Row:
    """Inverse of to_row. Reconstructs Program, ExecutionTrace, RowMeta, renders dict."""
    m = row["meta"]
    meta = RowMeta(
        tier=m["tier"],
        split=m["split"],
        bucket=m["bucket"],
        seed=m["seed"],
        axes=dict(m["axes"]),
        renders=tuple(m["renders"]),
    )
    instructions = tuple(_instruction_from_dict(d) for d in row["program"])
    program = Program.build(instructions)
    trace = ExecutionTrace(
        steps=[_step_from_dict(d) for d in row["trace"]["steps"]],
        output=list(row["trace"]["output"]),
        halted=row["trace"]["halted"],
    )
    renders = {name: _rendered_prompt_from_dict(d) for name, d in row["renders"].items()}
    return Row(program=program, trace=trace, meta=meta, renders=renders)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/test_schema.py -v`
Expected: 10 passing.

- [ ] **Step 5: Commit**

```bash
git -C /Users/sidgraph/FANC add tinyvm/data/schema.py tinyvm/data/tests/test_schema.py
git -C /Users/sidgraph/FANC commit -m "feat(tinyvm.data): from_row deserialiser + round-trip property test"
```

---

## Phase C — Configs

### Task 6: `EvalBucket` and `DatasetConfig` dataclasses

**Files:**
- Create: `tinyvm/data/configs.py`
- Create: `tinyvm/data/tests/test_configs.py`

Refs spec §6.1.

- [ ] **Step 1: Write the failing tests**

```python
# tinyvm/data/tests/test_configs.py
import random
import pytest

from tinyvm.data.configs import EvalBucket, DatasetConfig


def test_eval_bucket_is_frozen():
    b = EvalBucket(name="len_8", size=20_000, fixed_axes={"n": 8, "k": 4})
    with pytest.raises((AttributeError, TypeError)):
        b.size = 99  # type: ignore[misc]


def test_dataset_config_holds_required_fields():
    cfg = DatasetConfig(
        tier="tier0",
        train_size=100,
        train_axes=lambda rng: {"n": 4},
        eval_buckets=(EvalBucket(name="all", size=10, fixed_axes={"n": 4}),),
        build=lambda rng, axes: None,   # type: ignore[arg-type]
        renders=("direct",),
    )
    assert cfg.tier == "tier0"
    assert cfg.train_size == 100
    assert cfg.eval_buckets[0].size == 10
    assert cfg.renders == ("direct",)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/test_configs.py -v`
Expected: `ModuleNotFoundError: tinyvm.data.configs`.

- [ ] **Step 3: Write `tinyvm/data/configs.py`**

```python
"""Per-tier DatasetConfig literals. Data only — no logic.

Spec §6.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from tinyvm.isa import Program


@dataclass(frozen=True)
class EvalBucket:
    """One eval bucket. Becomes file `eval/<name>.jsonl`."""
    name: str
    size: int
    fixed_axes: dict[str, int | bool]


# A train-axes sampler: given an rng, return a dict of axes for one program.
import random as _random
TrainAxesSampler = Callable[[_random.Random], dict[str, int | bool]]

# A program builder: given an rng and concrete axes, return a Program.
ProgramBuilder = Callable[[_random.Random, dict[str, int | bool]], Program]


@dataclass(frozen=True)
class DatasetConfig:
    """A full dataset recipe. The CLI/library references by `tier` name."""
    tier: str
    train_size: int
    train_axes: TrainAxesSampler
    eval_buckets: tuple[EvalBucket, ...]
    build: ProgramBuilder
    renders: tuple[str, ...]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/test_configs.py -v`
Expected: 2 passing.

- [ ] **Step 5: Commit**

```bash
git -C /Users/sidgraph/FANC add tinyvm/data/configs.py tinyvm/data/tests/test_configs.py
git -C /Users/sidgraph/FANC commit -m "feat(tinyvm.data): EvalBucket and DatasetConfig dataclasses"
```

---

### Task 7: `TIER0` and `TIER1` configs

**Files:**
- Modify: `tinyvm/data/configs.py`
- Modify: `tinyvm/data/tests/test_configs.py`

Refs spec §6.2.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/data/tests/test_configs.py
from tinyvm.data.configs import TIER0, TIER1
from tinyvm.interpreter import run
from tinyvm.verifier import validate


def test_tier0_config_metadata():
    assert TIER0.tier == "tier0"
    assert TIER0.train_size == 100_000
    assert TIER0.eval_buckets == (EvalBucket(name="all", size=10_000, fixed_axes={"n": 8}),)
    assert TIER0.renders == ("direct",)


def test_tier0_build_produces_valid_programs():
    for seed in range(20):
        rng = random.Random(seed)
        axes = TIER0.train_axes(rng)
        assert 4 <= axes["n"] <= 8
        p = TIER0.build(rng, axes)
        assert validate(p)
        assert run(p).halted


def test_tier1_config_metadata():
    assert TIER1.tier == "tier1"
    assert TIER1.train_size == 200_000
    bucket_names = tuple(b.name for b in TIER1.eval_buckets)
    assert bucket_names == ("len_8", "len_16", "len_32", "len_48", "len_64", "len_96", "len_128")
    for b in TIER1.eval_buckets:
        assert b.size == 20_000
        assert b.fixed_axes["k"] == 4
    assert TIER1.renders == ("direct",)


def test_tier1_build_produces_valid_programs():
    for seed in range(20):
        rng = random.Random(seed)
        axes = TIER1.train_axes(rng)
        assert 8 <= axes["n"] <= 32
        assert axes["k"] in (2, 4, 8)
        p = TIER1.build(rng, axes)
        assert validate(p)
        assert run(p).halted
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/test_configs.py -v`
Expected: `ImportError: cannot import name 'TIER0'`.

- [ ] **Step 3: Append TIER0 + TIER1 to configs.py**

```python
# Append to tinyvm/data/configs.py
from tinyvm.generators import gen_counter, gen_register_trace


# ---- Tier 0 ----

def _tier0_train_axes(rng: _random.Random) -> dict[str, int | bool]:
    return {"n": rng.randint(4, 8)}


def _tier0_build(rng: _random.Random, axes: dict[str, int | bool]) -> Program:
    return gen_counter(n=axes["n"], rng=rng)


TIER0 = DatasetConfig(
    tier="tier0",
    train_size=100_000,
    train_axes=_tier0_train_axes,
    eval_buckets=(EvalBucket(name="all", size=10_000, fixed_axes={"n": 8}),),
    build=_tier0_build,
    renders=("direct",),
)


# ---- Tier 1 ----

def _tier1_train_axes(rng: _random.Random) -> dict[str, int | bool]:
    return {"n": rng.randint(8, 32), "k": rng.choice([2, 4, 8])}


def _tier1_build(rng: _random.Random, axes: dict[str, int | bool]) -> Program:
    return gen_register_trace(n=axes["n"], k=axes["k"], rng=rng)


TIER1 = DatasetConfig(
    tier="tier1",
    train_size=200_000,
    train_axes=_tier1_train_axes,
    eval_buckets=tuple(
        EvalBucket(name=f"len_{n}", size=20_000, fixed_axes={"n": n, "k": 4})
        for n in (8, 16, 32, 48, 64, 96, 128)
    ),
    build=_tier1_build,
    renders=("direct",),
)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/test_configs.py -v`
Expected: 6 passing.

- [ ] **Step 5: Commit**

```bash
git -C /Users/sidgraph/FANC add tinyvm/data/configs.py tinyvm/data/tests/test_configs.py
git -C /Users/sidgraph/FANC commit -m "feat(tinyvm.data): TIER0 and TIER1 dataset configs"
```

---

### Task 8: `TIER2` config + `CONFIGS` registry

**Files:**
- Modify: `tinyvm/data/configs.py`
- Modify: `tinyvm/data/tests/test_configs.py`

Refs spec §6.2.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/data/tests/test_configs.py
from tinyvm.data.configs import TIER2, CONFIGS


def test_tier2_config_metadata():
    assert TIER2.tier == "tier2"
    assert TIER2.train_size == 500_000
    bucket_names = tuple(b.name for b in TIER2.eval_buckets)
    assert bucket_names == ("easy", "medium", "hard", "ood_len_256")
    for b in TIER2.eval_buckets:
        assert b.size == 10_000
    assert TIER2.renders == ("direct", "cot")


def test_tier2_build_produces_valid_programs():
    # Build a handful at varying axes. gen_branched requires k >= 2; train_axes guarantees k in [4,8].
    for seed in range(10):
        rng = random.Random(seed)
        axes = TIER2.train_axes(rng)
        assert axes["k"] in (4, 6, 8)
        p = TIER2.build(rng, axes)
        assert validate(p)
        assert run(p).halted


def test_tier2_eval_buckets_build_validly():
    for bucket in TIER2.eval_buckets:
        for seed in range(5):
            rng = random.Random(seed * 7 + hash(bucket.name) % 10_000)
            p = TIER2.build(rng, dict(bucket.fixed_axes))
            assert validate(p), f"bucket={bucket.name} seed={seed} failed validate"
            assert run(p).halted


def test_configs_registry_has_three_tiers():
    assert set(CONFIGS.keys()) == {"tier0", "tier1", "tier2"}
    assert CONFIGS["tier0"] is TIER0
    assert CONFIGS["tier1"] is TIER1
    assert CONFIGS["tier2"] is TIER2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/test_configs.py -v`
Expected: `ImportError: cannot import name 'TIER2'`.

- [ ] **Step 3: Append TIER2 + CONFIGS to configs.py**

```python
# Append to tinyvm/data/configs.py
from tinyvm.generators import gen_branched, GenSpec


# ---- Tier 2 ----

def _tier2_train_axes(rng: _random.Random) -> dict[str, int | bool]:
    return {
        "n": rng.randint(16, 256),
        "k": rng.choice([4, 6, 8]),
        "b": rng.randint(1, 8),
        "l": rng.randint(0, 16),
        "use_stack": rng.random() < 0.5,
        "stack_frames": rng.randint(0, 2),
    }


def _tier2_build(rng: _random.Random, axes: dict[str, int | bool]) -> Program:
    return gen_branched(
        spec=GenSpec(
            n=axes["n"], k=axes["k"], b=axes["b"], l=axes["l"],
            use_stack=bool(axes["use_stack"]), stack_frames=axes["stack_frames"],
        ),
        rng=rng,
    )


TIER2 = DatasetConfig(
    tier="tier2",
    train_size=500_000,
    train_axes=_tier2_train_axes,
    eval_buckets=(
        EvalBucket(name="easy",
                   size=10_000,
                   fixed_axes={"n": 32, "k": 4, "b": 1, "l": 0, "use_stack": False, "stack_frames": 0}),
        EvalBucket(name="medium",
                   size=10_000,
                   fixed_axes={"n": 64, "k": 4, "b": 2, "l": 4, "use_stack": False, "stack_frames": 0}),
        EvalBucket(name="hard",
                   size=10_000,
                   fixed_axes={"n": 128, "k": 6, "b": 4, "l": 8, "use_stack": True, "stack_frames": 1}),
        EvalBucket(name="ood_len_256",
                   size=10_000,
                   fixed_axes={"n": 256, "k": 4, "b": 2, "l": 4, "use_stack": False, "stack_frames": 0}),
    ),
    build=_tier2_build,
    renders=("direct", "cot"),
)


# TODO Tier 4: gen_userop_trace returns UseropTrace (demos + target), not a
# single Program. Needs a row-variant schema. Defer to follow-up.

CONFIGS: dict[str, DatasetConfig] = {"tier0": TIER0, "tier1": TIER1, "tier2": TIER2}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/test_configs.py -v`
Expected: 10 passing.

- [ ] **Step 5: Commit**

```bash
git -C /Users/sidgraph/FANC add tinyvm/data/configs.py tinyvm/data/tests/test_configs.py
git -C /Users/sidgraph/FANC commit -m "feat(tinyvm.data): TIER2 config + CONFIGS registry"
```

---

## Phase D — Emit

### Task 9: `_row_seed` helper

**Files:**
- Create: `tinyvm/data/emit.py`
- Create: `tinyvm/data/tests/test_emit.py`

Refs spec §4 (decision 6), §7.2.

- [ ] **Step 1: Write the failing tests**

```python
# tinyvm/data/tests/test_emit.py
from tinyvm.data.emit import _row_seed


def test_row_seed_is_deterministic():
    assert _row_seed(0, "train", None, 0) == _row_seed(0, "train", None, 0)


def test_row_seed_changes_with_seed_base():
    assert _row_seed(0, "train", None, 0) != _row_seed(1, "train", None, 0)


def test_row_seed_changes_with_split():
    assert _row_seed(0, "train", None, 0) != _row_seed(0, "eval", None, 0)


def test_row_seed_changes_with_bucket():
    assert _row_seed(0, "eval", "len_8", 0) != _row_seed(0, "eval", "len_16", 0)


def test_row_seed_changes_with_index():
    assert _row_seed(0, "train", None, 0) != _row_seed(0, "train", None, 1)


def test_row_seed_is_64_bit_unsigned_int():
    s = _row_seed(0, "train", None, 0)
    assert isinstance(s, int)
    assert 0 <= s < 2**64
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/test_emit.py -v`
Expected: `ModuleNotFoundError: tinyvm.data.emit`.

- [ ] **Step 3: Write `tinyvm/data/emit.py` with `_row_seed`**

```python
"""Emit JSONL datasets to disk. Spec §7."""
from __future__ import annotations

import hashlib


def _row_seed(seed_base: int, split: str, bucket: str | None, index: int) -> int:
    """Derive a deterministic per-row seed. Collision-free across (split, bucket, index) triples."""
    key = f"{seed_base}|{split}|{bucket or ''}|{index}".encode()
    return int.from_bytes(hashlib.sha256(key).digest()[:8], "big")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/test_emit.py -v`
Expected: 6 passing.

- [ ] **Step 5: Commit**

```bash
git -C /Users/sidgraph/FANC add tinyvm/data/emit.py tinyvm/data/tests/test_emit.py
git -C /Users/sidgraph/FANC commit -m "feat(tinyvm.data): _row_seed deterministic per-row seed derivation"
```

---

### Task 10: `_build_renders` dispatcher

**Files:**
- Modify: `tinyvm/data/emit.py`
- Modify: `tinyvm/data/tests/test_emit.py`

Refs spec §7.2.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/data/tests/test_emit.py
import random
from tinyvm.data.emit import _build_renders
from tinyvm.data.schema import RenderedPrompt
from tinyvm.generators import gen_register_trace
from tinyvm.interpreter import run


def test_build_renders_produces_expected_modes():
    p = gen_register_trace(n=8, k=2, rng=random.Random(0))
    trace = run(p)
    out = _build_renders(p, trace, ("direct",))
    assert set(out.keys()) == {"direct"}
    assert isinstance(out["direct"], RenderedPrompt)
    assert len(out["direct"].input_ids) > 0
    assert len(out["direct"].target_ids) > 0
    assert "LOAD" in out["direct"].input_text or "ADD" in out["direct"].input_text


def test_build_renders_handles_multiple_modes():
    p = gen_register_trace(n=8, k=2, rng=random.Random(0))
    trace = run(p)
    out = _build_renders(p, trace, ("direct", "cot"))
    assert set(out.keys()) == {"direct", "cot"}
    # CoT target should be longer than direct target (carries per-step register file).
    assert len(out["cot"].target_ids) > len(out["direct"].target_ids)


def test_build_renders_empty_modes_returns_empty_dict():
    p = gen_register_trace(n=8, k=2, rng=random.Random(0))
    trace = run(p)
    out = _build_renders(p, trace, ())
    assert out == {}


def test_build_renders_unknown_mode_raises():
    import pytest
    p = gen_register_trace(n=8, k=2, rng=random.Random(0))
    trace = run(p)
    with pytest.raises(KeyError):
        _build_renders(p, trace, ("not_a_mode",))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/test_emit.py -v`
Expected: `ImportError: cannot import name '_build_renders'`.

- [ ] **Step 3: Append `_build_renders` to emit.py**

```python
# Append to tinyvm/data/emit.py
from typing import Callable

from tinyvm import tokeniser
from tinyvm.data.schema import RenderedPrompt
from tinyvm.interpreter import ExecutionTrace
from tinyvm.isa import Program


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/test_emit.py -v`
Expected: 10 passing.

- [ ] **Step 5: Commit**

```bash
git -C /Users/sidgraph/FANC add tinyvm/data/emit.py tinyvm/data/tests/test_emit.py
git -C /Users/sidgraph/FANC commit -m "feat(tinyvm.data): _build_renders dispatcher for direct + cot modes"
```

---

### Task 11: `_emit_split` writer

**Files:**
- Modify: `tinyvm/data/emit.py`
- Modify: `tinyvm/data/tests/test_emit.py`

Refs spec §7.2.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/data/tests/test_emit.py
import json
import hashlib
from pathlib import Path
from tinyvm.data.emit import _emit_split
from tinyvm.data.configs import TIER0


def test_emit_split_writes_n_rows_to_file(tmp_path: Path):
    out_path = tmp_path / "train.jsonl"
    n, h = _emit_split(TIER0, out_path, split="train", bucket=None,
                       n_rows=5, seed_base=0)
    assert n == 5
    assert isinstance(h, str) and len(h) == 64
    assert out_path.exists()
    lines = out_path.read_text().splitlines()
    assert len(lines) == 5
    # Each line is a valid JSON object with the expected top-level keys.
    for line in lines:
        row = json.loads(line)
        assert set(row.keys()) == {"meta", "program", "trace", "renders"}
        assert row["meta"]["tier"] == "tier0"
        assert row["meta"]["split"] == "train"
        assert row["meta"]["bucket"] is None


def test_emit_split_sha256_matches_file_content(tmp_path: Path):
    out_path = tmp_path / "train.jsonl"
    _, h = _emit_split(TIER0, out_path, split="train", bucket=None,
                       n_rows=3, seed_base=0)
    recomputed = hashlib.sha256(out_path.read_bytes()).hexdigest()
    assert h == recomputed


def test_emit_split_eval_uses_fixed_axes(tmp_path: Path):
    bucket = TIER0.eval_buckets[0]
    out_path = tmp_path / f"{bucket.name}.jsonl"
    _emit_split(TIER0, out_path, split="eval", bucket=bucket,
                n_rows=3, seed_base=0)
    for line in out_path.read_text().splitlines():
        row = json.loads(line)
        assert row["meta"]["split"] == "eval"
        assert row["meta"]["bucket"] == bucket.name
        assert row["meta"]["axes"] == {"n": 8}    # TIER0's bucket has fixed n=8


def test_emit_split_is_deterministic(tmp_path: Path):
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    _emit_split(TIER0, a, split="train", bucket=None, n_rows=4, seed_base=42)
    _emit_split(TIER0, b, split="train", bucket=None, n_rows=4, seed_base=42)
    assert a.read_bytes() == b.read_bytes()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/test_emit.py -v`
Expected: `ImportError: cannot import name '_emit_split'`.

- [ ] **Step 3: Append `_emit_split` to emit.py**

```python
# Append to tinyvm/data/emit.py
import json
import random
from pathlib import Path

from tinyvm.data.configs import DatasetConfig, EvalBucket
from tinyvm.data.schema import RowMeta, to_row
from tinyvm.interpreter import run


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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/test_emit.py -v`
Expected: 14 passing.

- [ ] **Step 5: Commit**

```bash
git -C /Users/sidgraph/FANC add tinyvm/data/emit.py tinyvm/data/tests/test_emit.py
git -C /Users/sidgraph/FANC commit -m "feat(tinyvm.data): _emit_split streaming JSONL writer with SHA-256"
```

---

### Task 12: `emit` public function + manifest

**Files:**
- Modify: `tinyvm/data/emit.py`
- Modify: `tinyvm/data/tests/test_emit.py`

Refs spec §7.1, §7.3.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/data/tests/test_emit.py
from datetime import datetime
from tinyvm.data.emit import emit


def _tiny_config():
    """A miniature TIER0 for fast emit tests."""
    from tinyvm.data.configs import EvalBucket, DatasetConfig, _tier0_train_axes, _tier0_build
    return DatasetConfig(
        tier="tier0",
        train_size=5,
        train_axes=_tier0_train_axes,
        eval_buckets=(EvalBucket(name="all", size=3, fixed_axes={"n": 8}),),
        build=_tier0_build,
        renders=("direct",),
    )


def test_emit_creates_layout(tmp_path: Path):
    cfg = _tiny_config()
    manifest_path = emit(cfg, tmp_path, seed_base=0)
    assert manifest_path == tmp_path / "tier0" / "manifest.json"
    assert (tmp_path / "tier0" / "train.jsonl").exists()
    assert (tmp_path / "tier0" / "eval" / "all.jsonl").exists()
    assert manifest_path.exists()


def test_emit_manifest_contents(tmp_path: Path):
    cfg = _tiny_config()
    manifest_path = emit(cfg, tmp_path, seed_base=7)
    manifest = json.loads(manifest_path.read_text())
    assert manifest["tier"] == "tier0"
    assert manifest["seed_base"] == 7
    assert "tinyvm_version" in manifest
    assert "tinyvm_commit" in manifest
    assert "generated_at" in manifest
    # generated_at parses as ISO8601.
    datetime.fromisoformat(manifest["generated_at"].rstrip("Z"))
    assert manifest["files"]["train.jsonl"]["rows"] == 5
    assert manifest["files"]["eval/all.jsonl"]["rows"] == 3
    # SHA-256 hashes are 64 hex chars.
    for entry in manifest["files"].values():
        assert len(entry["sha256"]) == 64


def test_emit_is_deterministic(tmp_path: Path):
    cfg = _tiny_config()
    a = tmp_path / "a"
    b = tmp_path / "b"
    emit(cfg, a, seed_base=42)
    emit(cfg, b, seed_base=42)
    # Train file bytes identical.
    assert (a / "tier0" / "train.jsonl").read_bytes() == (b / "tier0" / "train.jsonl").read_bytes()
    # Eval file bytes identical.
    assert (a / "tier0" / "eval" / "all.jsonl").read_bytes() == (b / "tier0" / "eval" / "all.jsonl").read_bytes()


def test_emit_different_seed_base_different_content(tmp_path: Path):
    cfg = _tiny_config()
    a = tmp_path / "a"
    b = tmp_path / "b"
    emit(cfg, a, seed_base=0)
    emit(cfg, b, seed_base=1)
    assert (a / "tier0" / "train.jsonl").read_bytes() != (b / "tier0" / "train.jsonl").read_bytes()
```

(Note: the `_tiny_config` helper imports private helpers `_tier0_train_axes` and `_tier0_build` from `configs.py`. They were defined as module-private with underscore. The test reaches into them; this is acceptable for tests in the sibling tests/ directory. If you'd rather expose them: just rename them without the underscore, but spec §6.2 keeps them private.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/test_emit.py -v`
Expected: `ImportError: cannot import name 'emit'`.

- [ ] **Step 3: Append `emit` + version/commit helpers to emit.py**

```python
# Append to tinyvm/data/emit.py
import subprocess
from datetime import datetime, timezone


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
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return manifest_path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/test_emit.py -v`
Expected: 18 passing.

- [ ] **Step 5: Commit**

```bash
git -C /Users/sidgraph/FANC add tinyvm/data/emit.py tinyvm/data/tests/test_emit.py
git -C /Users/sidgraph/FANC commit -m "feat(tinyvm.data): emit() public function + manifest writer"
```

---

## Phase E — Load

### Task 13: `load_jsonl` + `load_split`

**Files:**
- Create: `tinyvm/data/load.py`
- Create: `tinyvm/data/tests/test_load.py`

Refs spec §8.

- [ ] **Step 1: Write the failing tests**

```python
# tinyvm/data/tests/test_load.py
import pytest
from pathlib import Path

from tinyvm.data.load import load_jsonl, load_split
from tinyvm.data.emit import emit
from tinyvm.data.configs import EvalBucket, DatasetConfig
from tinyvm.data.configs import _tier0_train_axes, _tier0_build


def _tiny_config():
    return DatasetConfig(
        tier="tier0",
        train_size=4,
        train_axes=_tier0_train_axes,
        eval_buckets=(EvalBucket(name="all", size=3, fixed_axes={"n": 8}),),
        build=_tier0_build,
        renders=("direct",),
    )


def test_load_jsonl_yields_rows(tmp_path: Path):
    emit(_tiny_config(), tmp_path, seed_base=0)
    rows = list(load_jsonl(tmp_path / "tier0" / "train.jsonl"))
    assert len(rows) == 4
    # Each row is a Row NamedTuple from schema.py.
    from tinyvm.data.schema import Row
    assert all(isinstance(r, Row) for r in rows)
    # The first row's program is well-formed.
    assert len(rows[0].program.instructions) > 0


def test_load_split_train(tmp_path: Path):
    emit(_tiny_config(), tmp_path, seed_base=0)
    rows = list(load_split(tmp_path / "tier0", split="train"))
    assert len(rows) == 4


def test_load_split_eval_requires_bucket(tmp_path: Path):
    emit(_tiny_config(), tmp_path, seed_base=0)
    with pytest.raises(ValueError, match="bucket required"):
        list(load_split(tmp_path / "tier0", split="eval"))


def test_load_split_eval_bucket(tmp_path: Path):
    emit(_tiny_config(), tmp_path, seed_base=0)
    rows = list(load_split(tmp_path / "tier0", split="eval", bucket="all"))
    assert len(rows) == 3
    assert all(r.meta.bucket == "all" for r in rows)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/test_load.py -v`
Expected: `ModuleNotFoundError: tinyvm.data.load`.

- [ ] **Step 3: Write `tinyvm/data/load.py`**

```python
"""Streaming JSONL reader. Spec §8."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

from tinyvm.data.schema import Row, from_row


def load_jsonl(path: Path) -> Iterator[Row]:
    """Stream rows from a single .jsonl file as Row(program, trace, meta, renders) tuples."""
    with Path(path).open() as f:
        for line in f:
            yield from_row(json.loads(line))


def load_split(
    dataset_dir: Path,
    split: str,
    bucket: str | None = None,
) -> Iterator[Row]:
    """Convenience: load all rows for a (split, bucket). Train: bucket=None."""
    dataset_dir = Path(dataset_dir)
    if split == "train":
        return load_jsonl(dataset_dir / "train.jsonl")
    if bucket is None:
        raise ValueError("bucket required for split='eval'")
    return load_jsonl(dataset_dir / "eval" / f"{bucket}.jsonl")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/test_load.py -v`
Expected: 4 passing.

- [ ] **Step 5: Commit**

```bash
git -C /Users/sidgraph/FANC add tinyvm/data/load.py tinyvm/data/tests/test_load.py
git -C /Users/sidgraph/FANC commit -m "feat(tinyvm.data): load_jsonl and load_split streaming readers"
```

---

### Task 14: `load_prompts` fast path + `load_manifest`

**Files:**
- Modify: `tinyvm/data/load.py`
- Modify: `tinyvm/data/tests/test_load.py`

Refs spec §8.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/data/tests/test_load.py
from tinyvm.data.load import load_prompts, load_manifest


def test_load_prompts_yields_id_tuples(tmp_path: Path):
    emit(_tiny_config(), tmp_path, seed_base=0)
    pairs = list(load_prompts(tmp_path / "tier0" / "train.jsonl", mode="direct"))
    assert len(pairs) == 4
    for input_ids, target_ids in pairs:
        assert isinstance(input_ids, list)
        assert isinstance(target_ids, list)
        assert all(isinstance(x, int) for x in input_ids)
        assert all(isinstance(x, int) for x in target_ids)


def test_load_prompts_raises_on_unknown_mode(tmp_path: Path):
    emit(_tiny_config(), tmp_path, seed_base=0)
    with pytest.raises(KeyError):
        list(load_prompts(tmp_path / "tier0" / "train.jsonl", mode="not_a_mode"))


def test_load_manifest_returns_dict(tmp_path: Path):
    emit(_tiny_config(), tmp_path, seed_base=0)
    manifest = load_manifest(tmp_path / "tier0")
    assert manifest["tier"] == "tier0"
    assert "files" in manifest


def test_load_manifest_raises_on_missing(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_manifest(tmp_path / "nonexistent")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/test_load.py -v`
Expected: `ImportError: cannot import name 'load_prompts'`.

- [ ] **Step 3: Append `load_prompts` and `load_manifest` to load.py**

```python
# Append to tinyvm/data/load.py

def load_prompts(path: Path, mode: str = "direct") -> Iterator[tuple[list[int], list[int]]]:
    """Fast path: stream just (input_ids, target_ids) for the chosen render mode.

    Skips reconstruction of Program/ExecutionTrace. Use this in DataLoader
    pipelines that don't need the IR.

    Raises KeyError if `mode` isn't present in a row's `renders` block.
    """
    with Path(path).open() as f:
        for line in f:
            row = json.loads(line)
            r = row["renders"][mode]
            yield r["input_ids"], r["target_ids"]


def load_manifest(dataset_dir: Path) -> dict:
    """Read manifest.json. Raises FileNotFoundError if missing — that means the emit was incomplete."""
    return json.loads((Path(dataset_dir) / "manifest.json").read_text())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/test_load.py -v`
Expected: 8 passing.

- [ ] **Step 5: Commit**

```bash
git -C /Users/sidgraph/FANC add tinyvm/data/load.py tinyvm/data/tests/test_load.py
git -C /Users/sidgraph/FANC commit -m "feat(tinyvm.data): load_prompts fast path + load_manifest"
```

---

## Phase F — CLI

### Task 15: `__main__.py` — `emit` subcommand

**Files:**
- Create: `tinyvm/data/__main__.py`
- Modify: `tinyvm/data/tests/test_emit.py` (add CLI tests)

Refs spec §9.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/data/tests/test_emit.py
import subprocess
import sys


def test_cli_emit_with_unknown_tier_exits_nonzero(tmp_path: Path):
    """Plumbing check: argparse parses, the CLI dispatches, unknown tier fails cleanly."""
    result = subprocess.run(
        [sys.executable, "-m", "tinyvm.data", "emit",
         "--tier", "tier99", "--out", str(tmp_path)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0
    assert "tier99" in result.stderr or "tier99" in result.stdout
```

(A positive-path CLI test that emits a full real tier would take ~minutes per run — too slow for the test suite. The verify-subcommand test in Task 16 uses a tiny tmp emit and exercises the CLI end-to-end at small scale.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/test_emit.py -v`
Expected: failing — CLI module doesn't exist yet.

- [ ] **Step 3: Write `tinyvm/data/__main__.py`**

```python
"""CLI: python -m tinyvm.data emit/verify ..."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tinyvm.data.configs import CONFIGS
from tinyvm.data.emit import emit


def _cmd_emit(args: argparse.Namespace) -> int:
    if args.tier not in CONFIGS:
        print(f"unknown tier: {args.tier} (known: {sorted(CONFIGS)})", file=sys.stderr)
        return 2
    config = CONFIGS[args.tier]
    out_dir = Path(args.out)
    manifest_path = emit(config, out_dir, seed_base=args.seed)
    print(f"manifest: {manifest_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tinyvm.data")
    subparsers = parser.add_subparsers(dest="command", required=True)

    emit_p = subparsers.add_parser("emit", help="emit a JSONL dataset")
    emit_p.add_argument("--tier", required=True, help="tier name (tier0, tier1, tier2)")
    emit_p.add_argument("--out", required=True, help="output directory")
    emit_p.add_argument("--seed", type=int, default=0, help="seed_base for determinism")
    emit_p.set_defaults(func=_cmd_emit)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/test_emit.py -v`
Expected: 19 passing (18 from prior tasks + 1 new unknown-tier CLI test).

- [ ] **Step 5: Commit**

```bash
git -C /Users/sidgraph/FANC add tinyvm/data/__main__.py tinyvm/data/tests/test_emit.py
git -C /Users/sidgraph/FANC commit -m "feat(tinyvm.data): __main__ CLI with emit subcommand"
```

---

### Task 16: `verify` subcommand

**Files:**
- Modify: `tinyvm/data/__main__.py`
- Modify: `tinyvm/data/tests/test_emit.py`

Refs spec §9.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/data/tests/test_emit.py

def test_cli_verify_returns_0_on_fresh_emit(tmp_path: Path):
    cfg = _tiny_config()
    emit(cfg, tmp_path, seed_base=0)
    result = subprocess.run(
        [sys.executable, "-m", "tinyvm.data", "verify",
         "--dataset", str(tmp_path / "tier0")],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, f"verify failed: {result.stderr}"


def test_cli_verify_returns_2_on_corrupted_file(tmp_path: Path):
    cfg = _tiny_config()
    emit(cfg, tmp_path, seed_base=0)
    # Corrupt the train file.
    train_path = tmp_path / "tier0" / "train.jsonl"
    train_path.write_text("corrupted line\n" + train_path.read_text())
    result = subprocess.run(
        [sys.executable, "-m", "tinyvm.data", "verify",
         "--dataset", str(tmp_path / "tier0")],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 2
    assert "train.jsonl" in result.stderr or "train.jsonl" in result.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/test_emit.py -v`
Expected: failing — verify subcommand not implemented.

- [ ] **Step 3: Add `verify` subcommand to `__main__.py`**

```python
# Append/edit tinyvm/data/__main__.py

import hashlib
from tinyvm.data.load import load_manifest


def _cmd_verify(args: argparse.Namespace) -> int:
    dataset_dir = Path(args.dataset)
    try:
        manifest = load_manifest(dataset_dir)
    except FileNotFoundError:
        print(f"manifest.json missing in {dataset_dir} — emit was incomplete", file=sys.stderr)
        return 2

    mismatches = []
    for relpath, expected in manifest["files"].items():
        path = dataset_dir / relpath
        if not path.exists():
            mismatches.append((relpath, "missing file"))
            continue
        actual_sha = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual_sha != expected["sha256"]:
            mismatches.append((relpath, f"sha256 mismatch: expected {expected['sha256']}, got {actual_sha}"))

    if mismatches:
        print(f"verify FAILED for {dataset_dir}:", file=sys.stderr)
        for relpath, reason in mismatches:
            print(f"  {relpath}: {reason}", file=sys.stderr)
        return 2
    print(f"verify OK: {dataset_dir} ({len(manifest['files'])} files)")
    return 0


# Then in main(), add the verify subparser BEFORE `args = parser.parse_args(argv)`:
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tinyvm.data")
    subparsers = parser.add_subparsers(dest="command", required=True)

    emit_p = subparsers.add_parser("emit", help="emit a JSONL dataset")
    emit_p.add_argument("--tier", required=True, help="tier name (tier0, tier1, tier2)")
    emit_p.add_argument("--out", required=True, help="output directory")
    emit_p.add_argument("--seed", type=int, default=0, help="seed_base for determinism")
    emit_p.set_defaults(func=_cmd_emit)

    verify_p = subparsers.add_parser("verify", help="re-hash files and compare against manifest")
    verify_p.add_argument("--dataset", required=True, help="path to dataset directory (e.g., data/tier1/)")
    verify_p.set_defaults(func=_cmd_verify)

    args = parser.parse_args(argv)
    return args.func(args)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/test_emit.py -v`
Expected: 21 passing (19 from prior tasks + 2 new verify subcommand tests).

- [ ] **Step 5: Commit**

```bash
git -C /Users/sidgraph/FANC add tinyvm/data/__main__.py tinyvm/data/tests/test_emit.py
git -C /Users/sidgraph/FANC commit -m "feat(tinyvm.data): verify CLI subcommand (re-hash + compare manifest)"
```

---

## Phase G — Pipeline integration tests

### Task 17: Trace-replay integration test

**Files:**
- Create: `tinyvm/data/tests/test_pipeline.py`

Refs spec §10 (Integration trace-replay).

- [ ] **Step 1: Write the failing test**

```python
# tinyvm/data/tests/test_pipeline.py
"""End-to-end pipeline tests. Spec §10."""
import random
from pathlib import Path

from tinyvm.data.configs import EvalBucket, DatasetConfig
from tinyvm.data.configs import (
    _tier0_train_axes, _tier0_build,
    _tier1_train_axes, _tier1_build,
)
from tinyvm.data.emit import emit
from tinyvm.data.load import load_jsonl
from tinyvm.interpreter import run


def _tiny_tier0():
    return DatasetConfig(
        tier="tier0", train_size=10, train_axes=_tier0_train_axes,
        eval_buckets=(EvalBucket(name="all", size=5, fixed_axes={"n": 8}),),
        build=_tier0_build, renders=("direct",),
    )


def _tiny_tier1():
    return DatasetConfig(
        tier="tier1", train_size=10, train_axes=_tier1_train_axes,
        eval_buckets=(EvalBucket(name="len_16", size=5, fixed_axes={"n": 16, "k": 4}),),
        build=_tier1_build, renders=("direct",),
    )


def test_trace_replay_tier0(tmp_path: Path):
    """Every loaded row's program re-runs to produce the trace's output."""
    emit(_tiny_tier0(), tmp_path, seed_base=0)
    for row in load_jsonl(tmp_path / "tier0" / "train.jsonl"):
        replayed = run(row.program)
        assert replayed.output == row.trace.output
        assert replayed.halted == row.trace.halted


def test_trace_replay_tier1(tmp_path: Path):
    emit(_tiny_tier1(), tmp_path, seed_base=0)
    for row in load_jsonl(tmp_path / "tier1" / "train.jsonl"):
        replayed = run(row.program)
        assert replayed.output == row.trace.output


def test_seed_reproducibility_per_row(tmp_path: Path):
    """Each row's program is reconstructable from row.meta.seed + row.meta.axes."""
    cfg = _tiny_tier1()
    emit(cfg, tmp_path, seed_base=0)
    for row in load_jsonl(tmp_path / "tier1" / "train.jsonl"):
        replayed = cfg.build(random.Random(row.meta.seed), row.meta.axes)
        assert replayed == row.program, f"row reconstruction failed for seed={row.meta.seed}"
```

- [ ] **Step 2: Run the test, verify it passes** (it should pass given the prior tasks)

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/test_pipeline.py -v`
Expected: 3 passing.

If `test_seed_reproducibility_per_row` fails: the train_axes sampler consumes random state from `rng` BEFORE `build` is called; replay needs to run the sampler first to reproduce the same axes, OR `row.meta.axes` must be passed in directly (skipping the sampler). The test uses the latter (passes `row.meta.axes` directly), so it should work because `build` only takes axes and rng, and `_tier1_build(rng, axes)` is determined by `(rng, axes)` together. Verify by reading the failing program if it does fail.

- [ ] **Step 3: Commit**

```bash
git -C /Users/sidgraph/FANC add tinyvm/data/tests/test_pipeline.py
git -C /Users/sidgraph/FANC commit -m "test(tinyvm.data): trace-replay and seed-reproducibility integration tests"
```

---

### Task 18: Render fidelity test + full-suite green

**Files:**
- Modify: `tinyvm/data/tests/test_pipeline.py`

Refs spec §10 (Render fidelity).

- [ ] **Step 1: Append the failing test**

```python
# Append to tinyvm/data/tests/test_pipeline.py
from tinyvm import tokeniser


def test_render_fidelity(tmp_path: Path):
    """Stored render IDs/text reproduce when re-rendered from the loaded Program."""
    emit(_tiny_tier0(), tmp_path, seed_base=0)
    for row in load_jsonl(tmp_path / "tier0" / "train.jsonl"):
        for mode in row.renders:
            stored = row.renders[mode]
            # Re-render from loaded program + trace.
            if mode == "direct":
                input_ids, target_ids = tokeniser.render_direct(row.program, row.trace)
                input_text, target_text = tokeniser.render_direct_text(row.program, row.trace)
            elif mode == "cot":
                input_ids, target_ids = tokeniser.render_cot(row.program, row.trace)
                input_text, target_text = tokeniser.render_cot_text(row.program, row.trace)
            else:
                continue
            assert stored.input_ids == input_ids
            assert stored.target_ids == target_ids
            assert stored.input_text == input_text
            assert stored.target_text == target_text


def test_full_suite_green(tmp_path: Path):
    """Smoke test: emit a tiny dataset for each tier, load it back, replay traces."""
    for cfg in (_tiny_tier0(), _tiny_tier1()):
        # Each tier emits to its own subdir to keep paths clean: tmp_path/<tier>/<tier>/...
        # would double-nest, so use separate parent dirs.
        out_root = tmp_path / f"emit_{cfg.tier}"
        out_root.mkdir()
        emit(cfg, out_root, seed_base=0)
        for row in load_jsonl(out_root / cfg.tier / "train.jsonl"):
            assert run(row.program).output == row.trace.output
```

- [ ] **Step 2: Run the tests**

Run: `cd /Users/sidgraph/FANC && pytest tinyvm/data/tests/ -v`
Expected: all passing.

- [ ] **Step 3: Run the entire repo test suite**

Run: `cd /Users/sidgraph/FANC && pytest -v 2>&1 | tail -20`
Expected: 123 pre-existing tinyvm tests + ~46 new tinyvm.data tests = ~169 passing, 0 skipped (except the documented full-tier CLI skip).

- [ ] **Step 4: Commit**

```bash
git -C /Users/sidgraph/FANC add tinyvm/data/tests/test_pipeline.py
git -C /Users/sidgraph/FANC commit -m "test(tinyvm.data): render-fidelity test + full-suite green"
```

---

## Spec coverage map

| Spec section | Implemented by |
|---|---|
| §2 Scope (5 src files + 5 test files) | Tasks 1–18 |
| §3 Decisions (rich IR, pre-render, hybrid layout, single-process, Python config, hash seeds, manifest, Op-by-name) | Embedded across all phases |
| §4 Module structure | Task 1 (scaffolding) + each Phase places its files |
| §5 Schema (RowMeta, RenderedPrompt, Row, to_row, from_row, round-trip) | Tasks 2–5 |
| §6 Configs (EvalBucket, DatasetConfig, TIER0/1/2, CONFIGS) | Tasks 6–8 |
| §7 Emit (`_row_seed`, `_build_renders`, `_emit_split`, `emit`, manifest) | Tasks 9–12 |
| §8 Load (`load_jsonl`, `load_split`, `load_prompts`, `load_manifest`) | Tasks 13–14 |
| §9 CLI (emit + verify subcommands) | Tasks 15–16 |
| §10 Testing (8 layers) | Distributed across all tasks; integration in Tasks 17–18 |
| §11 Risks (drift, stale prompts, slow emit, disk, partial manifest, JSON overhead) | Mitigations live in the spec; the CLI verify + determinism tests + skip-on-full-emit address them in code |
| §12 Open questions deferred | Editorial calls; can be edited by changing `configs.py` literals without changing pipeline code |

---

## Plan complete

Plan complete and saved to `docs/superpowers/plans/2026-05-16-tinyvm-data-pipeline.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
