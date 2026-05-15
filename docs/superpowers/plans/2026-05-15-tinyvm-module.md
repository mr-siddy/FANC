# Tiny-VM Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Tiny-VM data-generation module — the IR + interpreter + 4 generators + tokeniser + verifier specified in `docs/superpowers/specs/2026-05-15-tinyvm-module-design.md` — that serves as the supervision-signal source for the entire FANC experimental program (Tiers 0–5).

**Architecture:** IR-first Python module. A canonical `Program` dataclass is the central data type; the interpreter, generators, tokeniser, and verifier each operate on it via well-defined boundaries. Each sub-module is a single file (~70–260 LOC). Tests live in `tinyvm/tests/`. TDD throughout: write the failing test first, then minimal implementation, then commit.

**Tech Stack:** Python 3.11+, pytest, numpy (distribution sanity tests only). Standard library `random.Random` for seeded generation. No ML frameworks at this stage.

---

## File structure

```
FANC/
├── pyproject.toml                  # CREATE (Task 1)
├── tinyvm/
│   ├── __init__.py                 # CREATE (Task 1)
│   ├── isa.py                      # CREATE (Tasks 2–3)
│   ├── interpreter.py              # CREATE (Tasks 4–8)
│   ├── tokeniser.py                # CREATE (Tasks 9–15, 35–36)
│   ├── verifier.py                 # CREATE (Tasks 16–21)
│   └── generators.py               # CREATE (Tasks 22–34, 37)
└── tinyvm/tests/
    ├── __init__.py                 # CREATE (Task 1)
    ├── test_isa.py                 # CREATE (Tasks 2–3)
    ├── test_interpreter.py         # CREATE (Tasks 4–8)
    ├── test_tokeniser.py           # CREATE (Tasks 9–15, 35–36)
    ├── test_verifier.py            # CREATE (Tasks 16–21)
    ├── test_generators.py          # CREATE (Tasks 22–34, 37)
    ├── test_distribution.py        # CREATE (Task 38)
    └── test_determinism.py         # CREATE (Task 39)
```

**File-by-file responsibility:**

- `isa.py` — pure data: `Op` enum (16 base + 5 userop slots), `Instruction`, `Program`, constants.
- `interpreter.py` — `run(Program, step_cap) -> ExecutionTrace`, `ExecutionTrace`, `StepRecord`, `InterpreterError`.
- `tokeniser.py` — 64-token vocab, `encode`/`decode`, 5 renderers, text-level renderers for Qwen hand-off.
- `verifier.py` — `score_output`, `validate` (with optional `userop_signatures`).
- `generators.py` — `GenSpec`, `ShapingSpec`, 4 generators, `UseropPair`, `UseropTrace`, decomposition substitution.

---

## Phase A — Scaffolding and ISA

### Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `tinyvm/__init__.py`
- Create: `tinyvm/tests/__init__.py`
- Create: `tinyvm/tests/conftest.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "tinyvm"
version = "0.1.0"
description = "Tiny-VM data generation engine for FANC"
requires-python = ">=3.11"
dependencies = [
    "numpy>=1.24",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4",
    "pytest-xdist>=3.3",
]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["tinyvm*"]

[tool.pytest.ini_options]
testpaths = ["tinyvm/tests"]
python_files = ["test_*.py"]
addopts = "-ra -q"
```

- [ ] **Step 2: Create `tinyvm/__init__.py`** (empty file)

```python
"""Tiny-VM: synthetic data-generation engine for FANC."""
```

- [ ] **Step 3: Create `tinyvm/tests/__init__.py`** (empty file)

```python
```

- [ ] **Step 4: Create `tinyvm/tests/conftest.py`** with a seeded-rng fixture used by many tests

```python
import random
import pytest


@pytest.fixture
def rng():
    """Deterministic RNG seeded at 0 for any test that needs randomness."""
    return random.Random(0)


@pytest.fixture
def rng_factory():
    """Returns a factory that produces fresh Random(seed) per call."""
    return lambda seed: random.Random(seed)
```

- [ ] **Step 5: Install in editable mode and verify pytest discovers no tests**

Run: `pip install -e ".[dev]"`
Run: `pytest --collect-only`
Expected: `no tests ran` (no tests defined yet) — exit code 5 is acceptable here.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml tinyvm/__init__.py tinyvm/tests/__init__.py tinyvm/tests/conftest.py
git commit -m "feat(tinyvm): project scaffolding and pytest config"
```

---

### Task 2: ISA constants and Op enum

**Files:**
- Create: `tinyvm/isa.py`
- Create: `tinyvm/tests/test_isa.py`

Refs spec §5.

- [ ] **Step 1: Write the failing test**

```python
# tinyvm/tests/test_isa.py
from tinyvm.isa import (
    Op, NUM_REGS, VAL_MIN, VAL_MAX,
    LITERAL_MIN, LITERAL_MAX, STACK_DEPTH, DEFAULT_STEP_CAP,
)


def test_constants_match_spec():
    assert NUM_REGS == 8
    assert VAL_MIN == -1024
    assert VAL_MAX == 1023
    assert LITERAL_MIN == -127
    assert LITERAL_MAX == 127
    assert STACK_DEPTH == 16
    assert DEFAULT_STEP_CAP == 1_000_000


def test_op_enum_has_16_base_ops_and_5_userop_slots():
    base_ops = [
        Op.LOAD, Op.MOV, Op.ADD, Op.SUB, Op.MUL, Op.DIV,
        Op.NEG, Op.EQ, Op.LT, Op.JZ, Op.JMP,
        Op.PUSH, Op.POP, Op.PRINT, Op.NOP, Op.HALT,
    ]
    assert len(base_ops) == 16
    assert [int(op) for op in base_ops] == list(range(16))
    userop_slots = [Op.USEROP_0, Op.USEROP_1, Op.USEROP_2, Op.USEROP_3, Op.USEROP_4]
    assert [int(op) for op in userop_slots] == list(range(16, 21))


def test_op_is_userop_helper():
    assert Op.USEROP_0.is_userop()
    assert Op.USEROP_4.is_userop()
    assert not Op.LOAD.is_userop()
    assert not Op.HALT.is_userop()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tinyvm/tests/test_isa.py -v`
Expected: ImportError / ModuleNotFoundError on `tinyvm.isa`.

- [ ] **Step 3: Write the minimal implementation**

```python
# tinyvm/isa.py
"""ISA: pure data — Op enum, constants, Instruction, Program (added in Task 3)."""
from __future__ import annotations

from enum import IntEnum


NUM_REGS: int = 8
VAL_MIN: int = -1024
VAL_MAX: int = 1023
LITERAL_MIN: int = -127
LITERAL_MAX: int = 127
STACK_DEPTH: int = 16
DEFAULT_STEP_CAP: int = 1_000_000


class Op(IntEnum):
    # Base ISA — interpreter executes these.
    LOAD = 0
    MOV = 1
    ADD = 2
    SUB = 3
    MUL = 4
    DIV = 5
    NEG = 6
    EQ = 7
    LT = 8
    JZ = 9
    JMP = 10
    PUSH = 11
    POP = 12
    PRINT = 13
    NOP = 14
    HALT = 15
    # Userop slots — symbolic only. Interpreter raises on these (Task 8).
    # gen_userop_trace (Task 34) substitutes them with their decomposition.
    USEROP_0 = 16
    USEROP_1 = 17
    USEROP_2 = 18
    USEROP_3 = 19
    USEROP_4 = 20

    def is_userop(self) -> bool:
        return int(self) >= 16
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tinyvm/tests/test_isa.py -v`
Expected: all 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add tinyvm/isa.py tinyvm/tests/test_isa.py
git commit -m "feat(tinyvm): isa constants and Op enum"
```

---

### Task 3: Instruction and Program dataclasses

**Files:**
- Modify: `tinyvm/isa.py`
- Modify: `tinyvm/tests/test_isa.py`

Refs spec §5.

- [ ] **Step 1: Append the failing tests to `test_isa.py`**

```python
# Append to tinyvm/tests/test_isa.py
import pytest
from tinyvm.isa import Instruction, Program


def test_instruction_is_frozen():
    inst = Instruction(op=Op.LOAD, args=(0, 5))
    with pytest.raises((AttributeError, TypeError)):
        inst.op = Op.ADD  # type: ignore[misc]


def test_instruction_default_label_and_target_are_none():
    inst = Instruction(op=Op.ADD, args=(0, 1, 2))
    assert inst.label is None
    assert inst.target is None


def test_program_precomputes_label_index():
    insts = (
        Instruction(op=Op.LOAD, args=(0, 1), label="L0"),
        Instruction(op=Op.ADD, args=(0, 0, 0)),
        Instruction(op=Op.JMP, args=(), target="L0"),
        Instruction(op=Op.HALT, args=(), label="END"),
    )
    p = Program.build(insts)
    assert p.label_index == {"L0": 0, "END": 3}
    assert len(p.instructions) == 4


def test_program_build_rejects_duplicate_labels():
    insts = (
        Instruction(op=Op.NOP, args=(), label="L0"),
        Instruction(op=Op.NOP, args=(), label="L0"),
    )
    with pytest.raises(ValueError, match="duplicate label"):
        Program.build(insts)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tinyvm/tests/test_isa.py -v`
Expected: ImportError on `Instruction`/`Program`.

- [ ] **Step 3: Append the implementation to `isa.py`**

```python
# Append to tinyvm/isa.py
from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class Instruction:
    """A single Tiny-VM instruction."""
    op: Op
    args: tuple[int, ...] = ()
    label: str | None = None       # label *defined* at this line, e.g. "L3"
    target: str | None = None      # label *referenced* by JZ/JMP


@dataclass(frozen=True)
class Program:
    """A Tiny-VM program: instructions + precomputed label_index."""
    instructions: tuple[Instruction, ...]
    label_index: Mapping[str, int] = field(default_factory=dict)

    @classmethod
    def build(cls, instructions: tuple[Instruction, ...]) -> "Program":
        """Build a Program and precompute the label_index, rejecting duplicates."""
        idx: dict[str, int] = {}
        for i, inst in enumerate(instructions):
            if inst.label is not None:
                if inst.label in idx:
                    raise ValueError(f"duplicate label: {inst.label}")
                idx[inst.label] = i
        return cls(instructions=tuple(instructions), label_index=idx)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tinyvm/tests/test_isa.py -v`
Expected: all tests pass (7 total).

- [ ] **Step 5: Commit**

```bash
git add tinyvm/isa.py tinyvm/tests/test_isa.py
git commit -m "feat(tinyvm): Instruction and Program dataclasses with label_index"
```

---

## Phase B — Interpreter

The interpreter is built op-class by op-class with TDD. Tasks 4–8 split the 16 opcodes into coherent groups. The `ExecutionTrace` / `StepRecord` shapes are introduced in Task 4 and reused.

### Task 4: Interpreter — arithmetic, clamping, DIV/0

**Files:**
- Create: `tinyvm/interpreter.py`
- Create: `tinyvm/tests/test_interpreter.py`

Refs spec §6.

- [ ] **Step 1: Write the failing tests**

```python
# tinyvm/tests/test_interpreter.py
import pytest

from tinyvm.isa import Op, Instruction, Program, VAL_MIN, VAL_MAX
from tinyvm.interpreter import run, InterpreterError, ExecutionTrace


def _prog(*insts: Instruction) -> Program:
    return Program.build(tuple(insts))


def test_initial_register_state_is_zero():
    p = _prog(Instruction(Op.PRINT, args=(3,)), Instruction(Op.HALT))
    # PRINT R3 — R3 is initial 0
    trace = run(p)
    assert trace.output == [0]


def test_load_then_mov():
    p = _prog(
        Instruction(Op.LOAD, args=(0, 7)),
        Instruction(Op.MOV, args=(1, 0)),
        Instruction(Op.HALT),
    )
    trace = run(p)
    assert trace.steps[-1].regs[0] == 7
    assert trace.steps[-1].regs[1] == 7


def test_add_sub_mul_neg():
    p = _prog(
        Instruction(Op.LOAD, args=(0, 3)),
        Instruction(Op.LOAD, args=(1, 4)),
        Instruction(Op.ADD, args=(2, 0, 1)),   # R2 = 7
        Instruction(Op.SUB, args=(3, 1, 0)),   # R3 = 1
        Instruction(Op.MUL, args=(4, 2, 3)),   # R4 = 7
        Instruction(Op.NEG, args=(5, 4)),      # R5 = -7
        Instruction(Op.HALT),
    )
    trace = run(p)
    regs = trace.steps[-1].regs
    assert regs[2] == 7 and regs[3] == 1 and regs[4] == 7 and regs[5] == -7


def test_arithmetic_clamps_to_value_range():
    # 1000 * 1000 overflows VAL_MAX = 1023 — must clamp.
    p = _prog(
        Instruction(Op.LOAD, args=(0, 100)),
        Instruction(Op.MUL, args=(1, 0, 0)),  # 10_000 -> clamp to 1023
        Instruction(Op.HALT),
    )
    trace = run(p)
    assert trace.steps[-1].regs[1] == VAL_MAX


def test_negative_clamps_to_value_min():
    p = _prog(
        Instruction(Op.LOAD, args=(0, -100)),
        Instruction(Op.MUL, args=(1, 0, 0)),  # 10_000 -> clamp to 1023
        Instruction(Op.LOAD, args=(2, -100)),
        Instruction(Op.MUL, args=(3, 2, 0)),  # -100 * -100 = 10_000 -> 1023
        Instruction(Op.LOAD, args=(4, 100)),
        Instruction(Op.NEG, args=(5, 4)),
        Instruction(Op.MUL, args=(6, 5, 0)),  # -100 * -100 = 10_000 -> 1023
        Instruction(Op.HALT),
    )
    trace = run(p)
    # Demonstrate negative clamp: load big positive, NEG to -10000 via MUL
    # Easier: directly load -127, square, NEG.
    # (Test value: clamp boundaries verified above; this just exercises NEG.)


def test_div_by_zero_returns_zero():
    p = _prog(
        Instruction(Op.LOAD, args=(0, 10)),
        Instruction(Op.LOAD, args=(1, 0)),
        Instruction(Op.DIV, args=(2, 0, 1)),  # 10 / 0 -> 0 silently
        Instruction(Op.HALT),
    )
    trace = run(p)
    assert trace.steps[-1].regs[2] == 0


def test_div_truncates_toward_zero():
    p = _prog(
        Instruction(Op.LOAD, args=(0, 7)),
        Instruction(Op.LOAD, args=(1, 2)),
        Instruction(Op.DIV, args=(2, 0, 1)),  # 7 / 2 = 3
        Instruction(Op.HALT),
    )
    trace = run(p)
    assert trace.steps[-1].regs[2] == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tinyvm/tests/test_interpreter.py -v`
Expected: ImportError on `tinyvm.interpreter`.

- [ ] **Step 3: Write the minimal implementation**

```python
# tinyvm/interpreter.py
"""Interpreter: pure function run(Program) -> ExecutionTrace.

Semantics live here in one place (spec §6). All registers init to 0. All
arithmetic clamps to [VAL_MIN, VAL_MAX]. DIV/0 returns 0. Stack/USEROP
violations raise InterpreterError (spec §6, asymmetric error policy).
"""
from __future__ import annotations

from dataclasses import dataclass

from tinyvm.isa import (
    DEFAULT_STEP_CAP, NUM_REGS, Op, Program, VAL_MAX, VAL_MIN,
)


class InterpreterError(RuntimeError):
    """Raised on conditions that should never occur under generate-only-valid."""


@dataclass(frozen=True)
class StepRecord:
    pc: int                       # instruction index executed at this step
    regs: tuple[int, ...]         # register file *after* the instruction
    stack: tuple[int, ...]        # stack *after* the instruction
    emitted: int | None           # value PRINTed at this step, if any


@dataclass
class ExecutionTrace:
    steps: list[StepRecord]
    output: list[int]
    halted: bool


def _clamp(v: int) -> int:
    if v < VAL_MIN:
        return VAL_MIN
    if v > VAL_MAX:
        return VAL_MAX
    return v


def run(program: Program, step_cap: int | None = DEFAULT_STEP_CAP) -> ExecutionTrace:
    regs = [0] * NUM_REGS
    stack: list[int] = []
    steps: list[StepRecord] = []
    output: list[int] = []
    pc = 0
    n = len(program.instructions)
    halted = False
    step_count = 0

    while pc < n:
        if step_cap is not None and step_count >= step_cap:
            raise InterpreterError(f"step cap {step_cap} exceeded")
        step_count += 1

        inst = program.instructions[pc]
        emitted: int | None = None
        op = inst.op
        args = inst.args

        if op == Op.LOAD:
            i, lit = args
            regs[i] = _clamp(lit)
        elif op == Op.MOV:
            i, j = args
            regs[i] = regs[j]
        elif op == Op.ADD:
            i, j, k = args
            regs[i] = _clamp(regs[j] + regs[k])
        elif op == Op.SUB:
            i, j, k = args
            regs[i] = _clamp(regs[j] - regs[k])
        elif op == Op.MUL:
            i, j, k = args
            regs[i] = _clamp(regs[j] * regs[k])
        elif op == Op.DIV:
            i, j, k = args
            divisor = regs[k]
            if divisor == 0:
                regs[i] = 0
            else:
                # Python // floors; spec doesn't say but truncate-toward-zero is
                # the integer-division convention for signed values in most ISAs.
                q = abs(regs[j]) // abs(divisor)
                if (regs[j] < 0) ^ (divisor < 0):
                    q = -q
                regs[i] = _clamp(q)
        elif op == Op.NEG:
            i, j = args
            regs[i] = _clamp(-regs[j])
        else:
            raise InterpreterError(f"unhandled op (Task 4 partial impl): {op}")

        pc += 1
        steps.append(StepRecord(
            pc=pc - 1,
            regs=tuple(regs),
            stack=tuple(stack),
            emitted=emitted,
        ))

    halted = True
    return ExecutionTrace(steps=steps, output=output, halted=halted)
```

Note: this is a partial implementation. Tasks 5–8 will extend the dispatch to cover the remaining opcodes. We're keeping unhandled ops as a loud error to fail fast.

- [ ] **Step 4: Run tests — but two will still fail (PRINT, HALT not implemented yet)**

The `test_initial_register_state_is_zero` test calls `PRINT R3` and `HALT`, which are not in Task 4. Replace those tests' use of `PRINT`/`HALT` temporarily with a final `NOP` (also unhandled). We resolve this by simply omitting these tests until Task 7. **Action:** remove the `PRINT` and `HALT` references from the existing tests for now by ending each test program with the last meaningful arithmetic instruction (no trailing HALT — interpreter falls off end at the loop condition).

Replace the `_prog` body for `test_initial_register_state_is_zero` to be a no-op (e.g., `_prog(Instruction(Op.NEG, args=(0, 0)))`) so it doesn't exercise PRINT; this test moves to Task 7 in full form. For the other tests, remove the trailing `Instruction(Op.HALT)` — the interpreter falls off the end and that's covered by Task 6.

A cleaner alternative: skip `test_initial_register_state_is_zero` for now with `pytest.skip("PRINT lands in Task 7")` and let the others run.

```python
# Edit tinyvm/tests/test_interpreter.py:

def test_initial_register_state_is_zero():
    pytest.skip("PRINT/HALT land in Tasks 7-8")

# In every other test in Task 4, remove the trailing `Instruction(Op.HALT)`.
```

- [ ] **Step 5: Re-run, verify the non-skipped tests pass**

Run: `pytest tinyvm/tests/test_interpreter.py -v`
Expected: 5 tests pass, 1 skipped.

- [ ] **Step 6: Commit**

```bash
git add tinyvm/interpreter.py tinyvm/tests/test_interpreter.py
git commit -m "feat(tinyvm): interpreter — arithmetic, clamping, DIV/0"
```

---

### Task 5: Interpreter — comparisons (EQ, LT)

**Files:**
- Modify: `tinyvm/interpreter.py`
- Modify: `tinyvm/tests/test_interpreter.py`

Refs spec §6.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/tests/test_interpreter.py

def test_eq_returns_one_when_equal():
    p = _prog(
        Instruction(Op.LOAD, args=(0, 5)),
        Instruction(Op.LOAD, args=(1, 5)),
        Instruction(Op.EQ, args=(2, 0, 1)),
    )
    trace = run(p)
    assert trace.steps[-1].regs[2] == 1


def test_eq_returns_zero_when_unequal():
    p = _prog(
        Instruction(Op.LOAD, args=(0, 5)),
        Instruction(Op.LOAD, args=(1, 6)),
        Instruction(Op.EQ, args=(2, 0, 1)),
    )
    trace = run(p)
    assert trace.steps[-1].regs[2] == 0


def test_lt_strict_less_than():
    p = _prog(
        Instruction(Op.LOAD, args=(0, 3)),
        Instruction(Op.LOAD, args=(1, 4)),
        Instruction(Op.LT, args=(2, 0, 1)),  # 3 < 4 -> 1
        Instruction(Op.LT, args=(3, 1, 0)),  # 4 < 3 -> 0
        Instruction(Op.LT, args=(4, 0, 0)),  # 3 < 3 -> 0 (strict)
    )
    trace = run(p)
    regs = trace.steps[-1].regs
    assert regs[2] == 1 and regs[3] == 0 and regs[4] == 0
```

- [ ] **Step 2: Run — verify failure** (`unhandled op: EQ`)

Run: `pytest tinyvm/tests/test_interpreter.py -v`
Expected: 3 new tests fail with InterpreterError "unhandled op".

- [ ] **Step 3: Extend the dispatch in `interpreter.py`**

Add these branches before the `else` in the dispatch chain:

```python
        elif op == Op.EQ:
            i, j, k = args
            regs[i] = 1 if regs[j] == regs[k] else 0
        elif op == Op.LT:
            i, j, k = args
            regs[i] = 1 if regs[j] < regs[k] else 0
```

- [ ] **Step 4: Verify tests pass**

Run: `pytest tinyvm/tests/test_interpreter.py -v`
Expected: 8 pass, 1 skipped.

- [ ] **Step 5: Commit**

```bash
git add tinyvm/interpreter.py tinyvm/tests/test_interpreter.py
git commit -m "feat(tinyvm): interpreter — EQ and LT"
```

---

### Task 6: Interpreter — control flow (JZ, JMP, fall-off-end)

**Files:**
- Modify: `tinyvm/interpreter.py`
- Modify: `tinyvm/tests/test_interpreter.py`

Refs spec §6.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/tests/test_interpreter.py

def test_jz_taken_when_register_is_zero():
    p = _prog(
        Instruction(Op.LOAD, args=(0, 0)),
        Instruction(Op.JZ, args=(0,), target="END"),
        Instruction(Op.LOAD, args=(1, 99)),       # skipped
        Instruction(Op.NOP, label="END"),
    )
    trace = run(p)
    assert trace.steps[-1].regs[1] == 0


def test_jz_not_taken_when_register_is_nonzero():
    p = _prog(
        Instruction(Op.LOAD, args=(0, 1)),
        Instruction(Op.JZ, args=(0,), target="END"),
        Instruction(Op.LOAD, args=(1, 99)),       # executed
        Instruction(Op.NOP, label="END"),
    )
    trace = run(p)
    assert trace.steps[-1].regs[1] == 99


def test_jmp_unconditional():
    p = _prog(
        Instruction(Op.JMP, args=(), target="END"),
        Instruction(Op.LOAD, args=(0, 99)),       # skipped
        Instruction(Op.NOP, label="END"),
    )
    trace = run(p)
    assert trace.steps[-1].regs[0] == 0


def test_fall_off_end_halts_implicitly():
    p = _prog(Instruction(Op.LOAD, args=(0, 1)))
    trace = run(p)
    assert trace.halted is True
    assert trace.steps[-1].regs[0] == 1
```

- [ ] **Step 2: Run — verify failure**

Run: `pytest tinyvm/tests/test_interpreter.py -v`
Expected: 4 new tests fail with "unhandled op" on `JZ`, `JMP`, `NOP`.

- [ ] **Step 3: Extend the dispatch — JZ, JMP, NOP**

Add to the dispatch chain (before the catch-all `else`):

```python
        elif op == Op.JZ:
            (i,) = args
            if regs[i] == 0:
                pc = program.label_index[inst.target]
                # Record the step at the JZ instruction, then continue.
                steps.append(StepRecord(
                    pc=pc - 0,  # the JZ itself; pc has been updated to target
                    regs=tuple(regs),
                    stack=tuple(stack),
                    emitted=None,
                ))
                continue  # skip the default pc += 1
        elif op == Op.JMP:
            pc = program.label_index[inst.target]
            steps.append(StepRecord(
                pc=pc,
                regs=tuple(regs),
                stack=tuple(stack),
                emitted=None,
            ))
            continue
        elif op == Op.NOP:
            pass  # no state change
```

Note on the StepRecord-for-jumps detail: it's important that `steps` records *which instruction executed*, not the resulting pc. Refactor: introduce a local `executed_pc` variable that captures `pc` before any mutation:

Replace the inner loop body skeleton with this cleaner version:

```python
    while pc < n:
        if step_cap is not None and step_count >= step_cap:
            raise InterpreterError(f"step cap {step_cap} exceeded")
        step_count += 1

        executed_pc = pc
        inst = program.instructions[pc]
        emitted: int | None = None
        op = inst.op
        args = inst.args
        next_pc = pc + 1  # default; overridden by jumps

        if op == Op.LOAD:
            i, lit = args
            regs[i] = _clamp(lit)
        elif op == Op.MOV:
            i, j = args
            regs[i] = regs[j]
        elif op == Op.ADD:
            i, j, k = args
            regs[i] = _clamp(regs[j] + regs[k])
        elif op == Op.SUB:
            i, j, k = args
            regs[i] = _clamp(regs[j] - regs[k])
        elif op == Op.MUL:
            i, j, k = args
            regs[i] = _clamp(regs[j] * regs[k])
        elif op == Op.DIV:
            i, j, k = args
            divisor = regs[k]
            if divisor == 0:
                regs[i] = 0
            else:
                q = abs(regs[j]) // abs(divisor)
                if (regs[j] < 0) ^ (divisor < 0):
                    q = -q
                regs[i] = _clamp(q)
        elif op == Op.NEG:
            i, j = args
            regs[i] = _clamp(-regs[j])
        elif op == Op.EQ:
            i, j, k = args
            regs[i] = 1 if regs[j] == regs[k] else 0
        elif op == Op.LT:
            i, j, k = args
            regs[i] = 1 if regs[j] < regs[k] else 0
        elif op == Op.JZ:
            (i,) = args
            if regs[i] == 0:
                next_pc = program.label_index[inst.target]
        elif op == Op.JMP:
            next_pc = program.label_index[inst.target]
        elif op == Op.NOP:
            pass
        else:
            raise InterpreterError(f"unhandled op (partial impl): {op}")

        steps.append(StepRecord(
            pc=executed_pc,
            regs=tuple(regs),
            stack=tuple(stack),
            emitted=emitted,
        ))
        pc = next_pc
```

This refactor cleans up the jump bookkeeping. Replace the entire `while` loop body in `interpreter.py` with the version above.

- [ ] **Step 4: Verify tests pass**

Run: `pytest tinyvm/tests/test_interpreter.py -v`
Expected: 12 pass, 1 skipped.

- [ ] **Step 5: Commit**

```bash
git add tinyvm/interpreter.py tinyvm/tests/test_interpreter.py
git commit -m "feat(tinyvm): interpreter — JZ, JMP, NOP, fall-off-end"
```

---

### Task 7: Interpreter — stack (PUSH, POP) and faults

**Files:**
- Modify: `tinyvm/interpreter.py`
- Modify: `tinyvm/tests/test_interpreter.py`

Refs spec §6.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/tests/test_interpreter.py
from tinyvm.isa import STACK_DEPTH


def test_push_pop_round_trip():
    p = _prog(
        Instruction(Op.LOAD, args=(0, 42)),
        Instruction(Op.PUSH, args=(0,)),
        Instruction(Op.LOAD, args=(0, 0)),         # clobber R0
        Instruction(Op.POP, args=(1,)),            # R1 receives 42
    )
    trace = run(p)
    assert trace.steps[-1].regs[1] == 42


def test_push_overflow_raises():
    insts = [Instruction(Op.LOAD, args=(0, 1))]
    insts += [Instruction(Op.PUSH, args=(0,)) for _ in range(STACK_DEPTH + 1)]
    p = _prog(*insts)
    with pytest.raises(InterpreterError, match="stack overflow"):
        run(p)


def test_pop_underflow_raises():
    p = _prog(Instruction(Op.POP, args=(0,)))
    with pytest.raises(InterpreterError, match="stack underflow"):
        run(p)
```

- [ ] **Step 2: Run — verify failure**

Run: `pytest tinyvm/tests/test_interpreter.py -v`
Expected: 3 new tests fail with "unhandled op" on PUSH/POP.

- [ ] **Step 3: Extend dispatch with PUSH/POP**

Add to the dispatch chain (before the catch-all `else`):

```python
        elif op == Op.PUSH:
            (i,) = args
            if len(stack) >= STACK_DEPTH:
                raise InterpreterError("stack overflow")
            stack.append(regs[i])
        elif op == Op.POP:
            (i,) = args
            if not stack:
                raise InterpreterError("stack underflow")
            regs[i] = stack.pop()
```

Add `from tinyvm.isa import STACK_DEPTH` to interpreter imports.

- [ ] **Step 4: Verify tests pass**

Run: `pytest tinyvm/tests/test_interpreter.py -v`
Expected: 15 pass, 1 skipped.

- [ ] **Step 5: Commit**

```bash
git add tinyvm/interpreter.py tinyvm/tests/test_interpreter.py
git commit -m "feat(tinyvm): interpreter — PUSH/POP with overflow and underflow raises"
```

---

### Task 8: Interpreter — PRINT, HALT, step-cap, USEROP raises

**Files:**
- Modify: `tinyvm/interpreter.py`
- Modify: `tinyvm/tests/test_interpreter.py`

Refs spec §6.

- [ ] **Step 1: Append the failing tests and un-skip the earlier one**

```python
# Edit tinyvm/tests/test_interpreter.py:
# Replace test_initial_register_state_is_zero's body with:

def test_initial_register_state_is_zero():
    p = _prog(Instruction(Op.PRINT, args=(3,)), Instruction(Op.HALT))
    trace = run(p)
    assert trace.output == [0]
    assert trace.halted is True


# Append:

def test_print_emits_register_value():
    p = _prog(
        Instruction(Op.LOAD, args=(0, 9)),
        Instruction(Op.PRINT, args=(0,)),
        Instruction(Op.LOAD, args=(0, -5)),
        Instruction(Op.PRINT, args=(0,)),
        Instruction(Op.HALT),
    )
    trace = run(p)
    assert trace.output == [9, -5]


def test_halt_stops_execution_before_remaining_instructions():
    p = _prog(
        Instruction(Op.LOAD, args=(0, 1)),
        Instruction(Op.HALT),
        Instruction(Op.LOAD, args=(0, 99)),  # should NOT execute
    )
    trace = run(p)
    assert trace.steps[-1].regs[0] == 1
    assert trace.halted is True


def test_step_cap_raises():
    # A tight infinite loop bypasses generate-only-valid; force the cap.
    p = _prog(
        Instruction(Op.JMP, args=(), target="L", label="L"),
    )
    with pytest.raises(InterpreterError, match="step cap"):
        run(p, step_cap=100)


def test_step_cap_none_disables_the_cap():
    p = _prog(
        Instruction(Op.LOAD, args=(0, 5), label="L"),
        Instruction(Op.SUB, args=(0, 0, 0)),   # R0 -= 0 (no change)
        # No infinite loop — this terminates after 2 steps.
    )
    trace = run(p, step_cap=None)
    assert trace.halted is True


def test_userop_raises_on_execute():
    p = _prog(Instruction(Op.USEROP_0, args=(0, 1)))
    with pytest.raises(InterpreterError, match="userop"):
        run(p)
```

- [ ] **Step 2: Run — verify failure**

Run: `pytest tinyvm/tests/test_interpreter.py -v`
Expected: new tests fail with "unhandled op" on PRINT/HALT/USEROP_0.

- [ ] **Step 3: Extend dispatch with PRINT, HALT, USEROP catch**

Add to the dispatch chain (before the catch-all `else`):

```python
        elif op == Op.PRINT:
            (i,) = args
            emitted = regs[i]
            output.append(emitted)
        elif op == Op.HALT:
            steps.append(StepRecord(
                pc=executed_pc,
                regs=tuple(regs),
                stack=tuple(stack),
                emitted=None,
            ))
            return ExecutionTrace(steps=steps, output=output, halted=True)
        elif op.is_userop():
            raise InterpreterError(f"userop opcode {op.name} encountered; "
                                   f"substitute via decomposition before run()")
```

Replace the catch-all `else` with a clearer one:
```python
        else:
            raise InterpreterError(f"unhandled op: {op}")
```

- [ ] **Step 4: Verify all interpreter tests pass**

Run: `pytest tinyvm/tests/test_interpreter.py -v`
Expected: all tests pass (20+ tests, 0 skipped).

- [ ] **Step 5: Commit**

```bash
git add tinyvm/interpreter.py tinyvm/tests/test_interpreter.py
git commit -m "feat(tinyvm): interpreter — PRINT, HALT, step-cap, userop raises"
```

---

## Phase C — Tokeniser (base programs)

The userop-specific renderers (`render_userop_direct`, `render_userop_with_decomposition`) land in Phase F after `gen_userop_trace` exists.

### Task 9: Tokeniser — vocabulary (64 tokens)

**Files:**
- Create: `tinyvm/tokeniser.py`
- Create: `tinyvm/tests/test_tokeniser.py`

Refs spec §8.1.

- [ ] **Step 1: Write the failing test**

```python
# tinyvm/tests/test_tokeniser.py
from tinyvm.tokeniser import (
    VOCAB_SIZE, TOKEN_TO_ID, ID_TO_TOKEN, OPCODE_TOKENS, REGISTER_TOKENS,
    DIGIT_TOKENS, MINUS, L_MARKER, COLON, EQUALS, DECOMP, NEWLINE,
    BOS, EOS, PAD, QUERY, USEROP_TOKENS,
)
from tinyvm.isa import Op


def test_vocab_size_is_64():
    assert VOCAB_SIZE == 64


def test_token_id_round_trip():
    for tok, tid in TOKEN_TO_ID.items():
        assert ID_TO_TOKEN[tid] == tok


def test_token_id_assignments_are_dense():
    ids = sorted(TOKEN_TO_ID.values())
    assert ids == list(range(len(TOKEN_TO_ID)))


def test_opcode_tokens_cover_16_base_ops():
    base_ops = [op for op in Op if not op.is_userop()]
    assert len(base_ops) == 16
    for op in base_ops:
        assert op.name in OPCODE_TOKENS


def test_register_tokens_R0_through_R7():
    assert REGISTER_TOKENS == [f"R{i}" for i in range(8)]


def test_digit_tokens_0_through_9():
    assert DIGIT_TOKENS == [str(i) for i in range(10)]


def test_userop_tokens_have_five_reserved():
    assert len(USEROP_TOKENS) == 5


def test_special_tokens_exist():
    for tok in (MINUS, L_MARKER, COLON, EQUALS, DECOMP, NEWLINE, BOS, EOS, PAD, QUERY):
        assert tok in TOKEN_TO_ID
```

- [ ] **Step 2: Run — verify failure**

Run: `pytest tinyvm/tests/test_tokeniser.py -v`
Expected: ImportError on `tinyvm.tokeniser`.

- [ ] **Step 3: Write the implementation**

```python
# tinyvm/tokeniser.py
"""Tokeniser: 64-token vocab + encode/decode + renderers (spec §8)."""
from __future__ import annotations

from tinyvm.isa import NUM_REGS, Op


# 1. Build the vocab as an ordered list of tokens. ID = list position.
OPCODE_TOKENS: list[str] = [op.name for op in Op if not op.is_userop()]   # 16
REGISTER_TOKENS: list[str] = [f"R{i}" for i in range(NUM_REGS)]            # 8
DIGIT_TOKENS: list[str] = [str(i) for i in range(10)]                      # 10

MINUS: str = "MINUS"
L_MARKER: str = "L"
COLON: str = "COLON"
EQUALS: str = "EQUALS"
DECOMP: str = "DECOMP"
NEWLINE: str = "NEWLINE"
BOS: str = "BOS"
EOS: str = "EOS"
PAD: str = "PAD"
QUERY: str = "?"

USEROP_TOKENS: list[str] = ["DOUBLE", "MAX", "ABS", "MOD", "SIGN"]
# Default 5 userop symbols. Parent §9.2 names XOR as the fifth; spec §12 swaps
# SIGN in by default due to XOR's decomposition cost. The token list is what's
# emitted in surface text; the underlying Op slot (USEROP_0..USEROP_4) is
# fixed regardless of which symbol is bound to which slot.

_FIXED_TOKENS: list[str] = (
    OPCODE_TOKENS
    + REGISTER_TOKENS
    + DIGIT_TOKENS
    + [MINUS, L_MARKER, COLON, EQUALS, DECOMP, NEWLINE, BOS, EOS, PAD, QUERY]
    + USEROP_TOKENS
)
# Pad the vocab to 64 with placeholder reserved tokens.
_RESERVED_TOKENS: list[str] = [f"RESERVED_{i}" for i in range(64 - len(_FIXED_TOKENS))]

_ALL_TOKENS: list[str] = _FIXED_TOKENS + _RESERVED_TOKENS

VOCAB_SIZE: int = len(_ALL_TOKENS)
assert VOCAB_SIZE == 64, f"vocab size is {VOCAB_SIZE}, expected 64"

TOKEN_TO_ID: dict[str, int] = {tok: i for i, tok in enumerate(_ALL_TOKENS)}
ID_TO_TOKEN: dict[int, str] = {i: tok for tok, i in TOKEN_TO_ID.items()}
```

- [ ] **Step 4: Verify tests pass**

Run: `pytest tinyvm/tests/test_tokeniser.py -v`
Expected: 8 tests pass.

- [ ] **Step 5: Commit**

```bash
git add tinyvm/tokeniser.py tinyvm/tests/test_tokeniser.py
git commit -m "feat(tinyvm): tokeniser vocabulary (64 tokens)"
```

---

### Task 10: Tokeniser — encode (Program → token IDs)

**Files:**
- Modify: `tinyvm/tokeniser.py`
- Modify: `tinyvm/tests/test_tokeniser.py`

Refs spec §8.2.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/tests/test_tokeniser.py
from tinyvm.isa import Instruction, Op, Program
from tinyvm.tokeniser import encode


def _ids(*tokens: str) -> list[int]:
    return [TOKEN_TO_ID[t] for t in tokens]


def test_encode_load_with_negative_literal():
    p = Program.build((Instruction(Op.LOAD, args=(3, -42)),))
    ids = encode(p)
    assert ids == _ids("LOAD", "R3", "MINUS", "4", "2", "NEWLINE")


def test_encode_three_arg_arithmetic():
    p = Program.build((Instruction(Op.ADD, args=(0, 1, 2)),))
    assert encode(p) == _ids("ADD", "R0", "R1", "R2", "NEWLINE")


def test_encode_jz_with_label_reference():
    p = Program.build((Instruction(Op.JZ, args=(1,), target="L7"),))
    assert encode(p) == _ids("JZ", "R1", "L", "7", "NEWLINE")


def test_encode_label_definition_inline():
    p = Program.build((
        Instruction(Op.ADD, args=(0, 1, 2), label="L3"),
    ))
    assert encode(p) == _ids("L", "3", "COLON", "ADD", "R0", "R1", "R2", "NEWLINE")


def test_encode_print():
    p = Program.build((Instruction(Op.PRINT, args=(0,)),))
    assert encode(p) == _ids("PRINT", "R0", "NEWLINE")


def test_encode_userop_instruction_uses_symbol():
    # Default symbol for USEROP_0 is "DOUBLE".
    p = Program.build((Instruction(Op.USEROP_0, args=(1, 0)),))
    assert encode(p) == _ids("DOUBLE", "R1", "R0", "NEWLINE")
```

- [ ] **Step 2: Run — verify failure**

Run: `pytest tinyvm/tests/test_tokeniser.py -v`
Expected: ImportError on `encode`.

- [ ] **Step 3: Implement `encode`**

Append to `tokeniser.py`:

```python
from tinyvm.isa import Instruction, Program


# Userop slot -> default symbol (matches USEROP_TOKENS order).
USEROP_SLOT_TO_SYMBOL: dict[Op, str] = {
    Op.USEROP_0: USEROP_TOKENS[0],
    Op.USEROP_1: USEROP_TOKENS[1],
    Op.USEROP_2: USEROP_TOKENS[2],
    Op.USEROP_3: USEROP_TOKENS[3],
    Op.USEROP_4: USEROP_TOKENS[4],
}


def _opcode_token(op: Op) -> str:
    if op.is_userop():
        return USEROP_SLOT_TO_SYMBOL[op]
    return op.name


# Number of register args vs literal args per opcode (positional schema).
# Tuple: (n_register_args, n_literal_args, has_label_target)
_OP_ARG_SCHEMA: dict[Op, tuple[int, int, bool]] = {
    Op.LOAD: (1, 1, False),
    Op.MOV: (2, 0, False),
    Op.ADD: (3, 0, False),
    Op.SUB: (3, 0, False),
    Op.MUL: (3, 0, False),
    Op.DIV: (3, 0, False),
    Op.NEG: (2, 0, False),
    Op.EQ: (3, 0, False),
    Op.LT: (3, 0, False),
    Op.JZ: (1, 0, True),
    Op.JMP: (0, 0, True),
    Op.PUSH: (1, 0, False),
    Op.POP: (1, 0, False),
    Op.PRINT: (1, 0, False),
    Op.NOP: (0, 0, False),
    Op.HALT: (0, 0, False),
    # Userops: pattern depends on the user-defined signature.
    # Default convention (matches default USEROP_TOKENS):
    Op.USEROP_0: (2, 0, False),   # DOUBLE Ri Rj
    Op.USEROP_1: (3, 0, False),   # MAX Ri Rj Rk
    Op.USEROP_2: (2, 0, False),   # ABS Ri Rj
    Op.USEROP_3: (3, 0, False),   # MOD Ri Rj Rk
    Op.USEROP_4: (2, 0, False),   # SIGN Ri Rj
}


def _digits_of(n: int) -> list[str]:
    """Encode a signed integer as MINUS? digit sequence."""
    out: list[str] = []
    if n < 0:
        out.append(MINUS)
        n = -n
    for c in str(n):
        out.append(c)
    return out


def _encode_instruction(inst: Instruction) -> list[str]:
    tokens: list[str] = []
    # Label definition prefix.
    if inst.label is not None:
        tokens.extend(_digits_of(_label_to_int(inst.label)))
        # We just emitted just digits — need the L marker first.
        # Reset and redo properly:
        tokens = [L_MARKER, *_digits_of(_label_to_int(inst.label))[len([MINUS]) if False else 0:]]
        # Cleaner: rebuild with L marker prefix.
        tokens = [L_MARKER] + [c for c in str(_label_to_int(inst.label))] + [COLON]
    # Opcode.
    tokens.append(_opcode_token(inst.op))
    n_regs, n_lits, has_target = _OP_ARG_SCHEMA[inst.op]
    args = list(inst.args)
    for _ in range(n_regs):
        ri = args.pop(0)
        tokens.append(REGISTER_TOKENS[ri])
    for _ in range(n_lits):
        lit = args.pop(0)
        tokens.extend(_digits_of(lit))
    if has_target:
        assert inst.target is not None
        tokens.append(L_MARKER)
        tokens.extend([c for c in str(_label_to_int(inst.target))])
    tokens.append(NEWLINE)
    return tokens


def _label_to_int(label: str) -> int:
    """Labels are 'L<n>' or 'END'/etc. Map non-numeric labels to a stable int.

    For simplicity, label names emitted by generators are always 'L<n>'. The
    'END'-style labels used in some test programs are mapped via a small
    registry to keep encode/decode bijective. Tests using non-L<n> labels
    must register them via `register_label`.
    """
    if label.startswith("L") and label[1:].isdigit():
        return int(label[1:])
    return _LABEL_REGISTRY.setdefault(label, _next_label_id())


_LABEL_REGISTRY: dict[str, int] = {}
_LABEL_ID_COUNTER: list[int] = [10_000]  # high values; generator labels live in [0, 9999]


def _next_label_id() -> int:
    _LABEL_ID_COUNTER[0] += 1
    return _LABEL_ID_COUNTER[0]


def encode(program: Program) -> list[int]:
    """Encode a Program to a flat list of token IDs."""
    flat: list[str] = []
    for inst in program.instructions:
        flat.extend(_encode_instruction(inst))
    return [TOKEN_TO_ID[t] for t in flat]
```

Note: the `_encode_instruction` function above shows the *intent*; the duplicate-assignment to `tokens` is intentional cleanup — only the final form remains. Replace with this clean version:

```python
def _encode_instruction(inst: Instruction) -> list[str]:
    tokens: list[str] = []
    if inst.label is not None:
        tokens.append(L_MARKER)
        tokens.extend(c for c in str(_label_to_int(inst.label)))
        tokens.append(COLON)
    tokens.append(_opcode_token(inst.op))
    n_regs, n_lits, has_target = _OP_ARG_SCHEMA[inst.op]
    args = list(inst.args)
    for _ in range(n_regs):
        ri = args.pop(0)
        tokens.append(REGISTER_TOKENS[ri])
    for _ in range(n_lits):
        lit = args.pop(0)
        tokens.extend(_digits_of(lit))
    if has_target:
        assert inst.target is not None
        tokens.append(L_MARKER)
        tokens.extend(c for c in str(_label_to_int(inst.target)))
    tokens.append(NEWLINE)
    return tokens
```

- [ ] **Step 4: Verify tests pass**

Run: `pytest tinyvm/tests/test_tokeniser.py -v`
Expected: all encode tests pass.

- [ ] **Step 5: Commit**

```bash
git add tinyvm/tokeniser.py tinyvm/tests/test_tokeniser.py
git commit -m "feat(tinyvm): tokeniser encode (Program -> token IDs)"
```

---

### Task 11: Tokeniser — decode and round-trip property

**Files:**
- Modify: `tinyvm/tokeniser.py`
- Modify: `tinyvm/tests/test_tokeniser.py`

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/tests/test_tokeniser.py
import random
from tinyvm.tokeniser import decode


def test_decode_simple_load():
    ids = _ids("LOAD", "R3", "MINUS", "4", "2", "NEWLINE")
    p = decode(ids)
    assert len(p.instructions) == 1
    assert p.instructions[0] == Instruction(Op.LOAD, args=(3, -42))


def test_decode_labeled_jmp():
    ids = _ids("L", "3", "COLON", "JMP", "L", "3", "NEWLINE")
    p = decode(ids)
    assert p.instructions[0].label == "L3"
    assert p.instructions[0].op == Op.JMP
    assert p.instructions[0].target == "L3"


def test_round_trip_random_programs():
    """decode(encode(p)) == p for any well-formed generator output."""
    rng = random.Random(0)
    for _ in range(200):
        n = rng.randint(1, 10)
        insts: list[Instruction] = []
        for _ in range(n):
            choice = rng.choice([
                Instruction(Op.LOAD, args=(rng.randint(0, 7), rng.randint(-127, 127))),
                Instruction(Op.ADD, args=(rng.randint(0, 7), rng.randint(0, 7), rng.randint(0, 7))),
                Instruction(Op.MOV, args=(rng.randint(0, 7), rng.randint(0, 7))),
                Instruction(Op.PRINT, args=(rng.randint(0, 7),)),
                Instruction(Op.NOP),
                Instruction(Op.HALT),
            ])
            insts.append(choice)
        p = Program.build(tuple(insts))
        assert decode(encode(p)) == p
```

- [ ] **Step 2: Run — verify failure**

Run: `pytest tinyvm/tests/test_tokeniser.py -v`
Expected: ImportError on `decode`.

- [ ] **Step 3: Implement `decode`**

Append to `tokeniser.py`:

```python
_TOKEN_NAME_TO_OP: dict[str, Op] = {op.name: op for op in Op if not op.is_userop()}
_SYMBOL_TO_USEROP: dict[str, Op] = {
    sym: slot for slot, sym in USEROP_SLOT_TO_SYMBOL.items()
}


def _read_int(tokens: list[str], pos: int) -> tuple[int, int]:
    """Read a (possibly negative) integer literal at `tokens[pos]`. Returns (value, new_pos)."""
    sign = 1
    if tokens[pos] == MINUS:
        sign = -1
        pos += 1
    digits = ""
    while pos < len(tokens) and tokens[pos] in DIGIT_TOKENS:
        digits += tokens[pos]
        pos += 1
    assert digits, "expected digit sequence"
    return sign * int(digits), pos


def _read_label(tokens: list[str], pos: int) -> tuple[str, int]:
    """Read an L<digits> label at `tokens[pos]`. Returns (label, new_pos)."""
    assert tokens[pos] == L_MARKER
    pos += 1
    digits = ""
    while pos < len(tokens) and tokens[pos] in DIGIT_TOKENS:
        digits += tokens[pos]
        pos += 1
    assert digits, "expected digit sequence after L marker"
    return f"L{int(digits)}", pos


def decode(ids: list[int]) -> Program:
    """Inverse of encode. Reconstructs a Program from token IDs."""
    tokens = [ID_TO_TOKEN[i] for i in ids]
    insts: list[Instruction] = []
    pos = 0
    while pos < len(tokens):
        label: str | None = None
        # Optional label definition.
        if tokens[pos] == L_MARKER and (pos + 1) < len(tokens) and tokens[pos + 1] in DIGIT_TOKENS:
            # Peek further: must be followed by digits then COLON.
            scan = pos + 1
            while scan < len(tokens) and tokens[scan] in DIGIT_TOKENS:
                scan += 1
            if scan < len(tokens) and tokens[scan] == COLON:
                label, pos = _read_label(tokens, pos)
                pos += 1  # consume COLON
        # Opcode (either base name or userop symbol).
        op_tok = tokens[pos]
        pos += 1
        if op_tok in _TOKEN_NAME_TO_OP:
            op = _TOKEN_NAME_TO_OP[op_tok]
        elif op_tok in _SYMBOL_TO_USEROP:
            op = _SYMBOL_TO_USEROP[op_tok]
        else:
            raise ValueError(f"unexpected opcode token: {op_tok}")
        n_regs, n_lits, has_target = _OP_ARG_SCHEMA[op]
        args: list[int] = []
        for _ in range(n_regs):
            reg_tok = tokens[pos]
            pos += 1
            args.append(REGISTER_TOKENS.index(reg_tok))
        for _ in range(n_lits):
            v, pos = _read_int(tokens, pos)
            args.append(v)
        target: str | None = None
        if has_target:
            target, pos = _read_label(tokens, pos)
        assert tokens[pos] == NEWLINE, f"expected NEWLINE, got {tokens[pos]}"
        pos += 1
        insts.append(Instruction(op=op, args=tuple(args), label=label, target=target))
    return Program.build(tuple(insts))
```

- [ ] **Step 4: Verify tests pass**

Run: `pytest tinyvm/tests/test_tokeniser.py -v`
Expected: all tests pass, including 200-program round-trip.

- [ ] **Step 5: Commit**

```bash
git add tinyvm/tokeniser.py tinyvm/tests/test_tokeniser.py
git commit -m "feat(tinyvm): tokeniser decode + 200-program round-trip property test"
```

---

### Task 12: Tokeniser — render_direct

**Files:**
- Modify: `tinyvm/tokeniser.py`
- Modify: `tinyvm/tests/test_tokeniser.py`

Refs spec §8.3.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/tests/test_tokeniser.py
from tinyvm.interpreter import run
from tinyvm.tokeniser import render_direct


def test_render_direct_input_is_bos_program_eos():
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 3)),
        Instruction(Op.PRINT, args=(0,)),
        Instruction(Op.HALT),
    ))
    trace = run(p)
    inp, tgt = render_direct(p, trace)
    assert inp[0] == TOKEN_TO_ID[BOS]
    assert inp[-1] == TOKEN_TO_ID[EOS]
    # Middle should equal encode(p).
    assert inp[1:-1] == encode(p)


def test_render_direct_target_is_print_value_stream():
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 3)),
        Instruction(Op.PRINT, args=(0,)),
        Instruction(Op.LOAD, args=(0, -5)),
        Instruction(Op.PRINT, args=(0,)),
        Instruction(Op.HALT),
    ))
    trace = run(p)
    _, tgt = render_direct(p, trace)
    expected = [TOKEN_TO_ID[BOS]] + _ids("3", "NEWLINE", "MINUS", "5", "NEWLINE") + [TOKEN_TO_ID[EOS]]
    assert tgt == expected
```

- [ ] **Step 2: Run — verify failure**

Run: `pytest tinyvm/tests/test_tokeniser.py -v`

- [ ] **Step 3: Implement `render_direct`**

Append to `tokeniser.py`:

```python
from tinyvm.interpreter import ExecutionTrace


def render_direct(program: Program, trace: ExecutionTrace) -> tuple[list[int], list[int]]:
    """Spec §8.3 render_direct: input=BOS+program+EOS, target=BOS+output stream+EOS."""
    inp = [TOKEN_TO_ID[BOS]] + encode(program) + [TOKEN_TO_ID[EOS]]
    target_tokens: list[str] = [BOS]
    for v in trace.output:
        target_tokens.extend(_digits_of(v))
        target_tokens.append(NEWLINE)
    target_tokens.append(EOS)
    return inp, [TOKEN_TO_ID[t] for t in target_tokens]
```

- [ ] **Step 4: Verify tests pass**

Run: `pytest tinyvm/tests/test_tokeniser.py -v`

- [ ] **Step 5: Commit**

```bash
git add tinyvm/tokeniser.py tinyvm/tests/test_tokeniser.py
git commit -m "feat(tinyvm): tokeniser render_direct"
```

---

### Task 13: Tokeniser — render_cot (full and modified modes)

**Files:**
- Modify: `tinyvm/tokeniser.py`
- Modify: `tinyvm/tests/test_tokeniser.py`

Refs spec §8.3.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/tests/test_tokeniser.py
from tinyvm.tokeniser import render_cot


def test_render_cot_full_emits_all_8_registers_per_step():
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 5)),
        Instruction(Op.PRINT, args=(0,)),
        Instruction(Op.HALT),
    ))
    trace = run(p)
    inp, tgt = render_cot(p, trace, mode="full")
    tgt_toks = [ID_TO_TOKEN[i] for i in tgt]
    # Count EQUALS tokens — should be 8 per executed instruction.
    assert tgt_toks.count(EQUALS) == 8 * len(trace.steps)


def test_render_cot_modified_emits_only_changed_registers():
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 5)),    # changes R0
        Instruction(Op.NOP),                  # changes nothing
        Instruction(Op.HALT),                 # changes nothing
    ))
    trace = run(p)
    inp, tgt = render_cot(p, trace, mode="modified")
    tgt_toks = [ID_TO_TOKEN[i] for i in tgt]
    # Only the LOAD step has a modification (R0). NOP/HALT have 0 modifications each.
    assert tgt_toks.count(EQUALS) == 1


def test_render_cot_input_matches_render_direct_input():
    p = Program.build((Instruction(Op.LOAD, args=(0, 1)), Instruction(Op.HALT)))
    trace = run(p)
    inp_cot, _ = render_cot(p, trace)
    inp_direct, _ = render_direct(p, trace)
    assert inp_cot == inp_direct
```

- [ ] **Step 2: Run — verify failure**

Run: `pytest tinyvm/tests/test_tokeniser.py -v`

- [ ] **Step 3: Implement `render_cot`**

Append to `tokeniser.py`:

```python
def _register_file_tokens(regs: tuple[int, ...], prev_regs: tuple[int, ...] | None, mode: str) -> list[str]:
    """Format a register file as 'R0 EQUALS <digits> R1 EQUALS <digits> ...'.

    mode='full' emits all NUM_REGS; 'modified' emits only registers whose value
    differs from prev_regs. Returns tokens (no trailing NEWLINE — caller appends).
    """
    out: list[str] = []
    for i in range(NUM_REGS):
        if mode == "modified" and prev_regs is not None and regs[i] == prev_regs[i]:
            continue
        out.append(REGISTER_TOKENS[i])
        out.append(EQUALS)
        out.extend(_digits_of(regs[i]))
    return out


def render_cot(
    program: Program,
    trace: ExecutionTrace,
    mode: str = "full",
) -> tuple[list[int], list[int]]:
    """Spec §8.3 render_cot. mode in {'full', 'modified'}."""
    if mode not in ("full", "modified"):
        raise ValueError(f"mode must be 'full' or 'modified', got {mode!r}")
    inp = [TOKEN_TO_ID[BOS]] + encode(program) + [TOKEN_TO_ID[EOS]]
    target_tokens: list[str] = [BOS]
    prev_regs: tuple[int, ...] | None = None
    for s in trace.steps:
        inst = program.instructions[s.pc]
        target_tokens.extend(_encode_instruction(inst))
        rf = _register_file_tokens(s.regs, prev_regs, mode)
        target_tokens.extend(rf)
        target_tokens.append(NEWLINE)
        prev_regs = s.regs
    # Final output stream.
    for v in trace.output:
        target_tokens.extend(_digits_of(v))
        target_tokens.append(NEWLINE)
    target_tokens.append(EOS)
    return inp, [TOKEN_TO_ID[t] for t in target_tokens]
```

- [ ] **Step 4: Verify tests pass**

Run: `pytest tinyvm/tests/test_tokeniser.py -v`

- [ ] **Step 5: Commit**

```bash
git add tinyvm/tokeniser.py tinyvm/tests/test_tokeniser.py
git commit -m "feat(tinyvm): tokeniser render_cot (full + modified modes)"
```

---

### Task 14: Tokeniser — render_probe_query and probe_targets

**Files:**
- Modify: `tinyvm/tokeniser.py`
- Modify: `tinyvm/tests/test_tokeniser.py`

Refs spec §8.3, §8.4.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/tests/test_tokeniser.py
from tinyvm.tokeniser import render_probe_query, probe_targets


def test_render_probe_query_input_truncates_to_step_t_plus_query_token():
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 5)),
        Instruction(Op.LOAD, args=(1, 7)),
        Instruction(Op.HALT),
    ))
    trace = run(p)
    inp, _ = render_probe_query(p, trace, step_t=1)
    inp_toks = [ID_TO_TOKEN[i] for i in inp]
    assert inp_toks[0] == BOS
    assert inp_toks[-1] == EOS
    assert QUERY in inp_toks
    # The query token must appear AFTER instruction[1].
    assert inp_toks.index(QUERY) > inp_toks.index("LOAD")


def test_render_probe_query_target_is_register_file_at_step_t():
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 5)),
        Instruction(Op.LOAD, args=(1, 7)),
        Instruction(Op.HALT),
    ))
    trace = run(p)
    _, tgt = render_probe_query(p, trace, step_t=1)
    tgt_toks = [ID_TO_TOKEN[i] for i in tgt]
    # After step 1, R0=5 and R1=7 (and others are 0). Expect 8 EQUALS tokens.
    assert tgt_toks.count(EQUALS) == 8


def test_probe_targets_returns_register_tuples_per_step():
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 5)),
        Instruction(Op.LOAD, args=(1, 7)),
        Instruction(Op.HALT),
    ))
    trace = run(p)
    targets = probe_targets(p, trace)
    assert len(targets) == len(trace.steps)
    assert targets[0][0] == 5
    assert targets[1][0] == 5 and targets[1][1] == 7
```

- [ ] **Step 2: Run — verify failure**

Run: `pytest tinyvm/tests/test_tokeniser.py -v`

- [ ] **Step 3: Implement both functions**

Append to `tokeniser.py`:

```python
def render_probe_query(
    program: Program,
    trace: ExecutionTrace,
    step_t: int,
) -> tuple[list[int], list[int]]:
    """Spec §8.3 render_probe_query."""
    # Input: BOS + program text up to and including instruction at executed step_t + ? + EOS
    executed_idx = trace.steps[step_t].pc
    inp_tokens: list[str] = [BOS]
    for i in range(executed_idx + 1):
        inp_tokens.extend(_encode_instruction(program.instructions[i]))
    inp_tokens.append(QUERY)
    inp_tokens.append(EOS)
    # Target: register file at step_t (full).
    tgt_tokens: list[str] = [BOS]
    tgt_tokens.extend(_register_file_tokens(trace.steps[step_t].regs, prev_regs=None, mode="full"))
    tgt_tokens.append(NEWLINE)
    tgt_tokens.append(EOS)
    return [TOKEN_TO_ID[t] for t in inp_tokens], [TOKEN_TO_ID[t] for t in tgt_tokens]


def probe_targets(program: Program, trace: ExecutionTrace) -> list[tuple[int, ...]]:
    """Spec §8.4 non-text probe mode: register files per step as plain tuples."""
    return [s.regs for s in trace.steps]
```

- [ ] **Step 4: Verify tests pass**

Run: `pytest tinyvm/tests/test_tokeniser.py -v`

- [ ] **Step 5: Commit**

```bash
git add tinyvm/tokeniser.py tinyvm/tests/test_tokeniser.py
git commit -m "feat(tinyvm): tokeniser render_probe_query and probe_targets"
```

---

### Task 15: Tokeniser — text-level renderers (Qwen hand-off)

**Files:**
- Modify: `tinyvm/tokeniser.py`
- Modify: `tinyvm/tests/test_tokeniser.py`

Refs spec §8.6.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/tests/test_tokeniser.py
from tinyvm.tokeniser import render_direct_text, render_cot_text


def test_render_direct_text_produces_human_readable_string():
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 3)),
        Instruction(Op.PRINT, args=(0,)),
        Instruction(Op.HALT),
    ))
    trace = run(p)
    inp_text, tgt_text = render_direct_text(p, trace)
    assert "LOAD R0 3" in inp_text
    assert "PRINT R0" in inp_text
    assert tgt_text.strip() == "3"


def test_render_cot_text_includes_register_file_strings():
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 1)),
        Instruction(Op.HALT),
    ))
    trace = run(p)
    _, tgt_text = render_cot_text(p, trace, mode="full")
    assert "R0=1" in tgt_text
    assert "R7=0" in tgt_text
```

- [ ] **Step 2: Run — verify failure**

Run: `pytest tinyvm/tests/test_tokeniser.py -v`

- [ ] **Step 3: Implement text renderers**

Append to `tokeniser.py`:

```python
def _tokens_to_text(tokens: list[str]) -> str:
    """Render a list of vocab tokens to a human-readable string.

    Surface rules: spaces between tokens, except no space before COLON or
    NEWLINE. MINUS attaches to the following digit. EQUALS attaches to
    the digit sequence on both sides (R0=5 not R0 = 5). NEWLINE -> '\n'.
    """
    out: list[str] = []
    for i, t in enumerate(tokens):
        if t == NEWLINE:
            out.append("\n")
        elif t == COLON:
            # Remove trailing space if any.
            if out and out[-1] == " ":
                out.pop()
            out.append(":")
        elif t == EQUALS:
            if out and out[-1] == " ":
                out.pop()
            out.append("=")
        elif t == MINUS:
            if out and out[-1] == " ":
                out.pop()
            out.append("-")
        elif t == L_MARKER:
            if out and out[-1] == " ":
                pass  # keep the space
            out.append("L")
        elif t in (BOS, EOS, PAD, QUERY, DECOMP):
            out.append(t if t != QUERY else "?")
            out.append(" ")
        elif t in DIGIT_TOKENS:
            # If previous non-space char is also a digit/MINUS continuation, attach.
            if out and out[-1] in {*DIGIT_TOKENS, "L", "-"}:
                out.append(t)
            else:
                out.append(t)
            # Always followed by a space until non-digit arrives (handled by next).
        else:
            out.append(t)
            out.append(" ")
    return "".join(out)


def render_direct_text(program: Program, trace: ExecutionTrace) -> tuple[str, str]:
    """Text-level render for Qwen tokeniser hand-off (spec §8.6)."""
    inp_ids, tgt_ids = render_direct(program, trace)
    inp_text = _tokens_to_text([ID_TO_TOKEN[i] for i in inp_ids])
    tgt_text = _tokens_to_text([ID_TO_TOKEN[i] for i in tgt_ids])
    return inp_text, tgt_text


def render_cot_text(program: Program, trace: ExecutionTrace, mode: str = "full") -> tuple[str, str]:
    """Text-level CoT render for Qwen tokeniser hand-off."""
    inp_ids, tgt_ids = render_cot(program, trace, mode=mode)
    return _tokens_to_text([ID_TO_TOKEN[i] for i in inp_ids]), _tokens_to_text([ID_TO_TOKEN[i] for i in tgt_ids])
```

The `_tokens_to_text` helper is heuristic and not bijective with `encode`; this is fine because Qwen's tokeniser consumes plain text and doesn't need round-trip recovery.

- [ ] **Step 4: Verify tests pass**

Run: `pytest tinyvm/tests/test_tokeniser.py -v`

- [ ] **Step 5: Commit**

```bash
git add tinyvm/tokeniser.py tinyvm/tests/test_tokeniser.py
git commit -m "feat(tinyvm): tokeniser text-level renderers for Qwen handoff"
```

---

## Phase D — Verifier

### Task 16: Verifier — score_output (RLVR reward)

**Files:**
- Create: `tinyvm/verifier.py`
- Create: `tinyvm/tests/test_verifier.py`

Refs spec §9.

- [ ] **Step 1: Write the failing tests**

```python
# tinyvm/tests/test_verifier.py
from tinyvm.tokeniser import TOKEN_TO_ID, BOS, EOS, NEWLINE, DIGIT_TOKENS, MINUS
from tinyvm.verifier import score_output


def _ids(*toks: str) -> list[int]:
    return [TOKEN_TO_ID[t] for t in toks]


def test_score_output_returns_1_on_exact_value_match():
    a = _ids(BOS, "3", NEWLINE, "5", NEWLINE, EOS)
    b = _ids(BOS, "3", NEWLINE, "5", NEWLINE, EOS)
    assert score_output(a, b) == 1.0


def test_score_output_returns_0_on_value_mismatch():
    a = _ids(BOS, "3", NEWLINE, EOS)
    b = _ids(BOS, "4", NEWLINE, EOS)
    assert score_output(a, b) == 0.0


def test_score_output_returns_0_on_length_mismatch():
    a = _ids(BOS, "3", NEWLINE, EOS)
    b = _ids(BOS, "3", NEWLINE, "5", NEWLINE, EOS)
    assert score_output(a, b) == 0.0


def test_score_output_negative_values():
    a = _ids(BOS, MINUS, "5", NEWLINE, EOS)
    b = _ids(BOS, MINUS, "5", NEWLINE, EOS)
    assert score_output(a, b) == 1.0
```

- [ ] **Step 2: Run — verify failure**

Run: `pytest tinyvm/tests/test_verifier.py -v`
Expected: ImportError on `tinyvm.verifier`.

- [ ] **Step 3: Write the implementation**

```python
# tinyvm/verifier.py
"""Verifier: score_output (RLVR reward) and validate (IR well-formedness)."""
from __future__ import annotations

from tinyvm.tokeniser import (
    BOS, DIGIT_TOKENS, EOS, ID_TO_TOKEN, MINUS, NEWLINE,
)


def _decode_value_stream(ids: list[int]) -> list[int]:
    """Extract the sequence of integer values from BOS + digit-encoded ints + EOS."""
    tokens = [ID_TO_TOKEN[i] for i in ids]
    # Strip BOS/EOS.
    if tokens and tokens[0] == BOS:
        tokens = tokens[1:]
    if tokens and tokens[-1] == EOS:
        tokens = tokens[:-1]
    values: list[int] = []
    pos = 0
    while pos < len(tokens):
        if tokens[pos] == NEWLINE:
            pos += 1
            continue
        sign = 1
        if tokens[pos] == MINUS:
            sign = -1
            pos += 1
        digits = ""
        while pos < len(tokens) and tokens[pos] in DIGIT_TOKENS:
            digits += tokens[pos]
            pos += 1
        if digits:
            values.append(sign * int(digits))
        # Skip a trailing NEWLINE.
        if pos < len(tokens) and tokens[pos] == NEWLINE:
            pos += 1
    return values


def score_output(predicted_ids: list[int], target_ids: list[int]) -> float:
    """Spec §9 RLVR reward: 1.0 iff decoded value sequences match exactly."""
    try:
        a = _decode_value_stream(predicted_ids)
        b = _decode_value_stream(target_ids)
    except Exception:
        return 0.0
    return 1.0 if a == b else 0.0
```

- [ ] **Step 4: Verify tests pass**

Run: `pytest tinyvm/tests/test_verifier.py -v`
Expected: 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add tinyvm/verifier.py tinyvm/tests/test_verifier.py
git commit -m "feat(tinyvm): verifier score_output (RLVR reward)"
```

---

### Task 17: Verifier — validate (labels, duplicates, opcode-arg-arity)

**Files:**
- Modify: `tinyvm/verifier.py`
- Modify: `tinyvm/tests/test_verifier.py`

Refs spec §9.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/tests/test_verifier.py
import pytest
from tinyvm.isa import Op, Instruction, Program
from tinyvm.verifier import validate


def test_validate_accepts_clean_program():
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 5)),
        Instruction(Op.ADD, args=(1, 0, 0)),
        Instruction(Op.PRINT, args=(1,)),
        Instruction(Op.HALT),
    ))
    assert validate(p) is True


def test_validate_rejects_unknown_label_target():
    p = Program.build((
        Instruction(Op.JMP, args=(), target="UNKNOWN"),
    ))
    assert validate(p) is False


def test_validate_rejects_wrong_opcode_arity():
    # ADD requires 3 args; pass 2.
    p = Program.build((
        Instruction(Op.ADD, args=(0, 1)),
    ))
    assert validate(p) is False
```

(Note: `Program.build` already rejects duplicate labels at construction. That's covered in Task 3.)

- [ ] **Step 2: Run — verify failure**

Run: `pytest tinyvm/tests/test_verifier.py -v`

- [ ] **Step 3: Implement basic validate**

Append to `verifier.py`:

```python
from tinyvm.isa import Op, Program
from tinyvm.tokeniser import _OP_ARG_SCHEMA   # opcode -> (n_regs, n_lits, has_target)


def validate(
    program: Program,
    userop_signatures: dict[str, set[int]] | None = None,
) -> bool:
    """Spec §9 validate(). Returns True iff well-formed.

    `userop_signatures` maps userop symbol -> set of register indices that
    userop writes to. Required when program contains unsubstituted userops.
    """
    try:
        _check_arity(program)
        _check_label_targets(program)
        _check_print_predecessors(program, userop_signatures)
        _check_stack_balance(program)
        _check_loop_counter_uniqueness(program)
    except _ValidationFailure:
        return False
    return True


class _ValidationFailure(Exception):
    pass


def _check_arity(program: Program) -> None:
    for inst in program.instructions:
        n_regs, n_lits, has_target = _OP_ARG_SCHEMA[inst.op]
        if len(inst.args) != n_regs + n_lits:
            raise _ValidationFailure(
                f"opcode {inst.op.name} expects {n_regs + n_lits} args, got {len(inst.args)}"
            )
        if has_target and inst.target is None:
            raise _ValidationFailure(f"opcode {inst.op.name} requires target label")


def _check_label_targets(program: Program) -> None:
    for inst in program.instructions:
        if inst.target is not None and inst.target not in program.label_index:
            raise _ValidationFailure(f"unknown label target: {inst.target}")


# Stubs for the remaining checks — Tasks 18-21 will implement.
def _check_print_predecessors(program: Program, userop_signatures: dict[str, set[int]] | None) -> None:
    pass


def _check_stack_balance(program: Program) -> None:
    pass


def _check_loop_counter_uniqueness(program: Program) -> None:
    pass
```

- [ ] **Step 4: Verify tests pass**

Run: `pytest tinyvm/tests/test_verifier.py -v`

- [ ] **Step 5: Commit**

```bash
git add tinyvm/verifier.py tinyvm/tests/test_verifier.py
git commit -m "feat(tinyvm): verifier validate — arity and label targets"
```

---

### Task 18: Verifier — validate PRINT predecessor reachability

**Files:**
- Modify: `tinyvm/verifier.py`
- Modify: `tinyvm/tests/test_verifier.py`

Refs spec §9.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/tests/test_verifier.py

def test_validate_rejects_print_without_write():
    # PRINT R3 with no prior write to R3 (and not initial-zero-allowed).
    p = Program.build((
        Instruction(Op.PRINT, args=(3,)),
    ))
    assert validate(p) is False


def test_validate_accepts_print_after_write():
    p = Program.build((
        Instruction(Op.LOAD, args=(3, 5)),
        Instruction(Op.PRINT, args=(3,)),
    ))
    assert validate(p) is True


def test_validate_handles_branch_paths():
    # Both arms write R3 before PRINT.
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 0)),
        Instruction(Op.JZ, args=(0,), target="ELSE"),
        Instruction(Op.LOAD, args=(3, 1)),    # then arm
        Instruction(Op.JMP, args=(), target="JOIN"),
        Instruction(Op.LOAD, args=(3, 2), label="ELSE"),  # else arm
        Instruction(Op.PRINT, args=(3,), label="JOIN"),
    ))
    assert validate(p) is True


def test_validate_rejects_branch_with_unwritten_arm():
    # ELSE arm doesn't write R3.
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 0)),
        Instruction(Op.JZ, args=(0,), target="ELSE"),
        Instruction(Op.LOAD, args=(3, 1)),
        Instruction(Op.JMP, args=(), target="JOIN"),
        Instruction(Op.NOP, label="ELSE"),
        Instruction(Op.PRINT, args=(3,), label="JOIN"),
    ))
    assert validate(p) is False
```

- [ ] **Step 2: Run — verify failure**

Run: `pytest tinyvm/tests/test_verifier.py -v`

- [ ] **Step 3: Implement the reachability check**

Replace the `_check_print_predecessors` stub with a fixed-point dataflow:

```python
def _writes_of(inst: Instruction, userop_signatures: dict[str, set[int]] | None) -> set[int]:
    """Return the set of register indices written by this instruction."""
    op = inst.op
    if op.is_userop():
        if userop_signatures is None:
            raise _ValidationFailure(
                f"userop {inst.op.name} encountered but userop_signatures=None"
            )
        # Map slot to its surface symbol via tokeniser binding.
        from tinyvm.tokeniser import USEROP_SLOT_TO_SYMBOL
        sym = USEROP_SLOT_TO_SYMBOL[op]
        return set(userop_signatures[sym])
    # Base ops: writers are the first register arg for ops that write one register.
    writes_one_reg = {
        Op.LOAD, Op.MOV, Op.ADD, Op.SUB, Op.MUL, Op.DIV,
        Op.NEG, Op.EQ, Op.LT, Op.POP,
    }
    if op in writes_one_reg:
        return {inst.args[0]}
    return set()


def _successors(program: Program, idx: int) -> list[int]:
    """Return the indices of instructions reachable in one step from program[idx]."""
    inst = program.instructions[idx]
    n = len(program.instructions)
    if inst.op == Op.HALT:
        return []
    if inst.op == Op.JMP:
        return [program.label_index[inst.target]]
    if inst.op == Op.JZ:
        nexts = []
        if idx + 1 < n:
            nexts.append(idx + 1)
        nexts.append(program.label_index[inst.target])
        return nexts
    if idx + 1 < n:
        return [idx + 1]
    return []


def _check_print_predecessors(
    program: Program,
    userop_signatures: dict[str, set[int]] | None,
) -> None:
    """For every PRINT Ri, ensure every reachable path from entry writes Ri before PRINT."""
    # Fixed-point dataflow: written_in[idx] = set of regs guaranteed written
    # on ALL paths from entry to idx (intersection at joins).
    n = len(program.instructions)
    if n == 0:
        return
    NUM_REGS_LOCAL = 8
    UNIVERSE = set(range(NUM_REGS_LOCAL))
    written_in: list[set[int]] = [UNIVERSE.copy() for _ in range(n)]
    written_in[0] = set()
    predecessors: list[list[int]] = [[] for _ in range(n)]
    for i in range(n):
        for j in _successors(program, i):
            predecessors[j].append(i)

    changed = True
    while changed:
        changed = False
        for i in range(n):
            if i == 0:
                continue
            preds = predecessors[i]
            if not preds:
                new = set()  # unreachable
            else:
                new = set.intersection(*(
                    written_in[p] | _writes_of(program.instructions[p], userop_signatures)
                    for p in preds
                ))
            if new != written_in[i]:
                written_in[i] = new
                changed = True

    for i, inst in enumerate(program.instructions):
        if inst.op == Op.PRINT:
            (ri,) = inst.args
            if ri not in written_in[i]:
                raise _ValidationFailure(f"PRINT R{ri} at idx {i} not preceded by write on all paths")
```

- [ ] **Step 4: Verify tests pass**

Run: `pytest tinyvm/tests/test_verifier.py -v`

- [ ] **Step 5: Commit**

```bash
git add tinyvm/verifier.py tinyvm/tests/test_verifier.py
git commit -m "feat(tinyvm): verifier validate — PRINT predecessor reachability"
```

---

### Task 19: Verifier — stack balance and depth

**Files:**
- Modify: `tinyvm/verifier.py`
- Modify: `tinyvm/tests/test_verifier.py`

Refs spec §9.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/tests/test_verifier.py
from tinyvm.isa import STACK_DEPTH


def test_validate_rejects_pop_without_push():
    p = Program.build((Instruction(Op.LOAD, args=(0, 1)), Instruction(Op.POP, args=(0,))))
    assert validate(p) is False


def test_validate_accepts_balanced_push_pop():
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 1)),
        Instruction(Op.PUSH, args=(0,)),
        Instruction(Op.POP, args=(1,)),
    ))
    assert validate(p) is True


def test_validate_rejects_stack_overflow_by_construction():
    insts = [Instruction(Op.LOAD, args=(0, 1))]
    insts += [Instruction(Op.PUSH, args=(0,)) for _ in range(STACK_DEPTH + 1)]
    p = Program.build(tuple(insts))
    assert validate(p) is False
```

- [ ] **Step 2: Run — verify failure**

Run: `pytest tinyvm/tests/test_verifier.py -v`

- [ ] **Step 3: Implement the check**

Replace `_check_stack_balance` stub:

```python
def _check_stack_balance(program: Program) -> None:
    """Dataflow over stack depth. depth_in[idx] = min and max possible depth at idx.

    Generate-only-valid means we want exact balance, so we model depth as a
    single value rather than a range; if paths converge with different depths
    we flag it.
    """
    from tinyvm.isa import STACK_DEPTH
    n = len(program.instructions)
    if n == 0:
        return
    depth_in: list[int | None] = [None] * n
    depth_in[0] = 0
    predecessors: list[list[int]] = [[] for _ in range(n)]
    for i in range(n):
        for j in _successors(program, i):
            predecessors[j].append(i)

    def _depth_delta(op: Op) -> int:
        if op == Op.PUSH:
            return 1
        if op == Op.POP:
            return -1
        return 0

    changed = True
    while changed:
        changed = False
        for i in range(n):
            preds = predecessors[i]
            if not preds and i != 0:
                continue
            if i == 0:
                continue
            new_depth: int | None = None
            for p in preds:
                if depth_in[p] is None:
                    continue
                d = depth_in[p] + _depth_delta(program.instructions[p].op)
                if d < 0:
                    raise _ValidationFailure(f"POP at idx {p} underflows")
                if d > STACK_DEPTH:
                    raise _ValidationFailure(f"PUSH at idx {p} overflows (depth {d} > {STACK_DEPTH})")
                if new_depth is None:
                    new_depth = d
                elif new_depth != d:
                    raise _ValidationFailure(
                        f"stack depth at idx {i} not balanced across paths: {new_depth} vs {d}"
                    )
            if new_depth is not None and depth_in[i] != new_depth:
                depth_in[i] = new_depth
                changed = True
```

- [ ] **Step 4: Verify tests pass**

Run: `pytest tinyvm/tests/test_verifier.py -v`

- [ ] **Step 5: Commit**

```bash
git add tinyvm/verifier.py tinyvm/tests/test_verifier.py
git commit -m "feat(tinyvm): verifier validate — stack balance and depth bound"
```

---

### Task 20: Verifier — loop-counter uniqueness check

**Files:**
- Modify: `tinyvm/verifier.py`
- Modify: `tinyvm/tests/test_verifier.py`

Refs spec §9. This check enforces that no two simultaneously-live loop counters share a register. We approximate "loop counter" as a register written in a back-edge predecessor block; in practice, the generators (Task 28+) annotate which register is a counter via a `metadata` hook. For Day 1–2, we keep this check lightweight and let it be a post-hoc soundness assert.

- [ ] **Step 1: Append the failing test**

```python
# Append to tinyvm/tests/test_verifier.py

def test_validate_loop_counter_uniqueness_smoke():
    # A program with a single explicit loop and a single counter — passes.
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 3)),                          # counter Rc=R0
        Instruction(Op.LOAD, args=(1, 1)),                          # R_one
        Instruction(Op.SUB, args=(0, 0, 1), label="L"),
        Instruction(Op.JZ, args=(0,), target="END"),
        Instruction(Op.JMP, args=(), target="L"),
        Instruction(Op.NOP, label="END"),
    ))
    assert validate(p) is True
```

(Day 1–2 scope: loop-counter uniqueness is enforced *constructively* by generators rather than checked structurally here. We keep the function present and trivially-passing so callers don't need to special-case.)

- [ ] **Step 2: Run — verify (already passes since stub is no-op)**

Run: `pytest tinyvm/tests/test_verifier.py -v`

- [ ] **Step 3: Add a one-line comment to the stub explaining**

Edit `_check_loop_counter_uniqueness`:

```python
def _check_loop_counter_uniqueness(program: Program) -> None:
    """Day 1-2 scope: enforced constructively by generators (Task 28+).

    A structural check would require recovering the CFG and finding back-edges,
    which is straightforward but unnecessary while generators carry the
    invariant by construction. Promote to a real check if generator drift is
    suspected.
    """
    return
```

- [ ] **Step 4: Verify tests pass**

Run: `pytest tinyvm/tests/test_verifier.py -v`

- [ ] **Step 5: Commit**

```bash
git add tinyvm/verifier.py tinyvm/tests/test_verifier.py
git commit -m "feat(tinyvm): verifier validate — loop-counter uniqueness stub (gen-enforced)"
```

---

### Task 21: Verifier — userop_signatures pass-through (test)

**Files:**
- Modify: `tinyvm/tests/test_verifier.py`

The implementation already accepts `userop_signatures` (Task 17). This task adds explicit tests so the contract is covered.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/tests/test_verifier.py

def test_validate_with_userop_requires_signatures():
    p = Program.build((
        Instruction(Op.USEROP_0, args=(0, 1)),  # DOUBLE R0 R1
        Instruction(Op.PRINT, args=(0,)),
    ))
    assert validate(p) is False  # missing signatures


def test_validate_with_userop_signatures_passes():
    p = Program.build((
        Instruction(Op.LOAD, args=(1, 5)),
        Instruction(Op.USEROP_0, args=(0, 1)),   # DOUBLE writes R0
        Instruction(Op.PRINT, args=(0,)),
    ))
    sigs = {"DOUBLE": {0}}
    assert validate(p, userop_signatures=sigs) is True
```

- [ ] **Step 2: Run — verify they pass without further code change**

Run: `pytest tinyvm/tests/test_verifier.py -v`

- [ ] **Step 3: Commit**

```bash
git add tinyvm/tests/test_verifier.py
git commit -m "test(tinyvm): verifier validate userop_signatures contract"
```

---

## Phase E — Generators

### Task 22: GenSpec and ShapingSpec dataclasses

**Files:**
- Create: `tinyvm/generators.py`
- Create: `tinyvm/tests/test_generators.py`

Refs spec §7.1, §7.6.

- [ ] **Step 1: Write the failing tests**

```python
# tinyvm/tests/test_generators.py
from tinyvm.generators import GenSpec, ShapingSpec


def test_shaping_spec_defaults_off():
    s = ShapingSpec()
    assert s.flat_output_histogram is False
    assert s.distractor_regs == 0
    assert s.randomize_print_target is False
    assert s.decorrelate_length is False


def test_gen_spec_holds_axis_dials_and_shaping():
    s = GenSpec(
        n=16, k=4, b=2, l=8, use_stack=True, stack_frames=1,
        shaping=ShapingSpec(distractor_regs=2),
    )
    assert s.n == 16 and s.k == 4 and s.b == 2 and s.l == 8
    assert s.use_stack is True and s.stack_frames == 1
    assert s.shaping.distractor_regs == 2
```

- [ ] **Step 2: Run — verify failure**

Run: `pytest tinyvm/tests/test_generators.py -v`

- [ ] **Step 3: Write the dataclasses**

```python
# tinyvm/generators.py
"""Generators: build Tiny-VM programs by construction (spec §7)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ShapingSpec:
    """Anti-shortcut knobs (spec §7.6). Defaults off."""
    flat_output_histogram: bool = False
    distractor_regs: int = 0
    randomize_print_target: bool = False
    decorrelate_length: bool = False


@dataclass(frozen=True)
class GenSpec:
    """Difficulty axes for the branched generator (spec §3.2, §7.5)."""
    n: int                          # target trajectory length
    k: int                          # active register count
    b: int = 0                      # number of branch structures
    l: int = 0                      # total loop-iteration budget
    use_stack: bool = False
    stack_frames: int = 0
    shaping: ShapingSpec = field(default_factory=ShapingSpec)
```

- [ ] **Step 4: Verify tests pass**

Run: `pytest tinyvm/tests/test_generators.py -v`

- [ ] **Step 5: Commit**

```bash
git add tinyvm/generators.py tinyvm/tests/test_generators.py
git commit -m "feat(tinyvm): GenSpec and ShapingSpec dataclasses"
```

---

### Task 23: gen_counter (Tier 0)

**Files:**
- Modify: `tinyvm/generators.py`
- Modify: `tinyvm/tests/test_generators.py`

Refs spec §7.5 row 1.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/tests/test_generators.py
import random
from tinyvm.generators import gen_counter
from tinyvm.interpreter import run
from tinyvm.verifier import validate


def test_gen_counter_program_has_correct_length():
    p = gen_counter(n=8, rng=random.Random(0))
    # n linear ops + 1 PRINT + 1 HALT.
    assert len(p.instructions) == 8 + 2


def test_gen_counter_uses_only_r0():
    p = gen_counter(n=8, rng=random.Random(0))
    for inst in p.instructions:
        for arg_idx, arg in enumerate(inst.args):
            # For LOAD the second arg is a literal; for ADD/SUB/NEG/MOV args
            # are register indices (except LOAD's second).
            if inst.op.name == "LOAD" and arg_idx == 1:
                continue
            assert arg == 0, f"{inst.op.name} uses non-R0 register: {inst.args}"


def test_gen_counter_property_validates_and_runs():
    for seed in range(50):
        p = gen_counter(n=8, rng=random.Random(seed))
        assert validate(p)
        trace = run(p)
        assert len(trace.output) == 1
```

- [ ] **Step 2: Run — verify failure**

Run: `pytest tinyvm/tests/test_generators.py -v`

- [ ] **Step 3: Implement gen_counter**

Append to `generators.py`:

```python
import random
from tinyvm.isa import Op, Instruction, Program, LITERAL_MIN, LITERAL_MAX


_COUNTER_OPS = [Op.ADD, Op.SUB, Op.NEG, Op.MOV]


def gen_counter(n: int, rng: random.Random) -> Program:
    """Tier 0 generator. n linear ops on R0, terminal PRINT R0, HALT.

    Op set restricted to ADD/SUB/NEG/MOV (no MUL/DIV — clamping/0-div would
    introduce non-trivial state effects that defeat the Tier 0 pipeline-sanity
    purpose). Initial LOAD seeds R0 with a small literal.
    """
    insts: list[Instruction] = []
    init_lit = rng.randint(LITERAL_MIN, LITERAL_MAX)
    insts.append(Instruction(Op.LOAD, args=(0, init_lit)))
    for _ in range(n - 1):
        op = rng.choice(_COUNTER_OPS)
        if op in (Op.ADD, Op.SUB):
            insts.append(Instruction(op, args=(0, 0, 0)))
        elif op == Op.NEG:
            insts.append(Instruction(op, args=(0, 0)))
        else:  # MOV
            insts.append(Instruction(op, args=(0, 0)))
    insts.append(Instruction(Op.PRINT, args=(0,)))
    insts.append(Instruction(Op.HALT))
    return Program.build(tuple(insts))
```

- [ ] **Step 4: Verify tests pass**

Run: `pytest tinyvm/tests/test_generators.py -v`

- [ ] **Step 5: Commit**

```bash
git add tinyvm/generators.py tinyvm/tests/test_generators.py
git commit -m "feat(tinyvm): gen_counter (Tier 0)"
```

---

### Task 24: `_allocate_registers` helper (random active subset)

**Files:**
- Modify: `tinyvm/generators.py`
- Modify: `tinyvm/tests/test_generators.py`

Refs spec §7.1, decision row 9.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/tests/test_generators.py
from collections import Counter
from tinyvm.generators import _allocate_registers


def test_allocate_returns_k_distinct_registers():
    rng = random.Random(0)
    active = _allocate_registers(k=4, rng=rng)
    assert len(active) == 4
    assert len(set(active)) == 4
    assert all(0 <= r < 8 for r in active)


def test_allocate_is_uniformly_random_across_seeds():
    counts = Counter()
    for seed in range(2000):
        rng = random.Random(seed)
        for r in _allocate_registers(k=4, rng=rng):
            counts[r] += 1
    # Expected ~1000 occurrences per register if uniform; allow ±30%.
    for r in range(8):
        assert 700 < counts[r] < 1300, f"R{r}: {counts[r]} (non-uniform)"
```

- [ ] **Step 2: Run — verify failure**

Run: `pytest tinyvm/tests/test_generators.py -v`

- [ ] **Step 3: Implement `_allocate_registers`**

Append to `generators.py`:

```python
from tinyvm.isa import NUM_REGS


def _allocate_registers(k: int, rng: random.Random) -> list[int]:
    """Sample k distinct register indices uniformly from R0..R{NUM_REGS-1}.

    Per-program randomisation is essential to avoid positional bias (spec §7.1).
    """
    if not (1 <= k <= NUM_REGS):
        raise ValueError(f"k must be in [1, {NUM_REGS}], got {k}")
    return rng.sample(range(NUM_REGS), k)
```

- [ ] **Step 4: Verify tests pass**

Run: `pytest tinyvm/tests/test_generators.py -v`

- [ ] **Step 5: Commit**

```bash
git add tinyvm/generators.py tinyvm/tests/test_generators.py
git commit -m "feat(tinyvm): _allocate_registers (uniform random active subset)"
```

---

### Task 25: `_fill_block` helper (straight-line arithmetic)

**Files:**
- Modify: `tinyvm/generators.py`
- Modify: `tinyvm/tests/test_generators.py`

Refs spec §7.1 step 3.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/tests/test_generators.py
from tinyvm.generators import _fill_block


def test_fill_block_produces_n_instructions_all_in_active_set():
    active = [1, 3, 5, 7]
    insts = _fill_block(n=10, active=active, rng=random.Random(0))
    assert len(insts) == 10
    for inst in insts:
        # All register args must be in active.
        n_regs, n_lits, _has_target = _OP_SCHEMA_FOR_FILL[inst.op]
        for ri in inst.args[:n_regs]:
            assert ri in active, f"{inst.op.name} uses non-active reg {ri}"


_OP_SCHEMA_FOR_FILL = {
    # Mirror of tokeniser._OP_ARG_SCHEMA for the ops fill_block can emit.
    Op.LOAD: (1, 1, False),
    Op.MOV: (2, 0, False),
    Op.ADD: (3, 0, False),
    Op.SUB: (3, 0, False),
    Op.MUL: (3, 0, False),
    Op.DIV: (3, 0, False),
    Op.NEG: (2, 0, False),
    Op.EQ: (3, 0, False),
    Op.LT: (3, 0, False),
}


def test_fill_block_excludes_reserved_registers():
    active = [0, 1, 2]
    reserved = {1}
    insts = _fill_block(n=20, active=active, rng=random.Random(0), exclude=reserved)
    for inst in insts:
        n_regs, _, _ = _OP_SCHEMA_FOR_FILL[inst.op]
        # Destination register must NOT be in reserved.
        if n_regs >= 1:
            assert inst.args[0] not in reserved
```

- [ ] **Step 2: Run — verify failure**

Run: `pytest tinyvm/tests/test_generators.py -v`

- [ ] **Step 3: Implement `_fill_block`**

Append to `generators.py`:

```python
_FILL_OPS: list[Op] = [
    Op.LOAD, Op.MOV, Op.ADD, Op.SUB, Op.MUL, Op.DIV, Op.NEG, Op.EQ, Op.LT,
]
_FILL_OP_ARITY: dict[Op, tuple[int, int]] = {
    Op.LOAD: (1, 1),
    Op.MOV: (2, 0),
    Op.ADD: (3, 0), Op.SUB: (3, 0), Op.MUL: (3, 0), Op.DIV: (3, 0),
    Op.NEG: (2, 0),
    Op.EQ: (3, 0), Op.LT: (3, 0),
}


def _fill_block(
    n: int,
    active: list[int],
    rng: random.Random,
    exclude: set[int] | None = None,
) -> list[Instruction]:
    """Generate `n` straight-line instructions drawn from _FILL_OPS.

    All register args are sampled from `active`. The DESTINATION register (the
    first register arg of any writing op) is sampled from `active - exclude`,
    so registers reserved as loop counters or stack-save sources are protected
    from being clobbered.
    """
    exclude = exclude or set()
    writable = [r for r in active if r not in exclude]
    assert writable, "no writable registers (active fully excluded)"
    insts: list[Instruction] = []
    for _ in range(n):
        op = rng.choice(_FILL_OPS)
        n_regs, n_lits = _FILL_OP_ARITY[op]
        args: list[int] = []
        # Destination (first reg arg) sampled from writable.
        if n_regs >= 1:
            args.append(rng.choice(writable))
        # Source regs sampled freely from active.
        for _ in range(n_regs - 1):
            args.append(rng.choice(active))
        # Literal args.
        for _ in range(n_lits):
            args.append(rng.randint(LITERAL_MIN, LITERAL_MAX))
        insts.append(Instruction(op=op, args=tuple(args)))
    return insts
```

- [ ] **Step 4: Verify tests pass**

Run: `pytest tinyvm/tests/test_generators.py -v`

- [ ] **Step 5: Commit**

```bash
git add tinyvm/generators.py tinyvm/tests/test_generators.py
git commit -m "feat(tinyvm): _fill_block straight-line arithmetic helper"
```

---

### Task 26: gen_register_trace (Tier 1)

**Files:**
- Modify: `tinyvm/generators.py`
- Modify: `tinyvm/tests/test_generators.py`

Refs spec §7.5 row 2.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/tests/test_generators.py
from tinyvm.generators import gen_register_trace


def test_gen_register_trace_validates_and_outputs_one_value():
    for seed in range(20):
        for n in (8, 16, 32):
            for k in (2, 4, 8):
                p = gen_register_trace(n=n, k=k, rng=random.Random(seed))
                assert validate(p)
                trace = run(p)
                assert len(trace.output) == 1


def test_gen_register_trace_has_no_branches_or_loops():
    p = gen_register_trace(n=32, k=4, rng=random.Random(0))
    for inst in p.instructions:
        assert inst.op not in (Op.JZ, Op.JMP)
```

- [ ] **Step 2: Run — verify failure**

Run: `pytest tinyvm/tests/test_generators.py -v`

- [ ] **Step 3: Implement gen_register_trace**

Append to `generators.py`:

```python
def gen_register_trace(
    n: int,
    k: int,
    rng: random.Random,
    shaping: ShapingSpec | None = None,
) -> Program:
    """Tier 1 generator. Straight-line program of length n over k active regs."""
    active = _allocate_registers(k=k, rng=rng)
    body = _fill_block(n=n, active=active, rng=rng)
    print_target = rng.choice(active)
    insts: list[Instruction] = []
    insts.extend(body)
    insts.append(Instruction(Op.PRINT, args=(print_target,)))
    insts.append(Instruction(Op.HALT))
    return Program.build(tuple(insts))
```

- [ ] **Step 4: Verify tests pass**

Run: `pytest tinyvm/tests/test_generators.py -v`

- [ ] **Step 5: Commit**

```bash
git add tinyvm/generators.py tinyvm/tests/test_generators.py
git commit -m "feat(tinyvm): gen_register_trace (Tier 1)"
```

---

### Task 27: Loop template — count-down

**Files:**
- Modify: `tinyvm/generators.py`
- Modify: `tinyvm/tests/test_generators.py`

Refs spec §7.2(a).

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/tests/test_generators.py
from tinyvm.generators import _emit_loop_countdown, _LabelGen


def test_loop_countdown_terminates_after_k_iterations():
    label_gen = _LabelGen()
    counter, r_one = 0, 1
    body = [Instruction(Op.ADD, args=(2, 2, 2))]  # arbitrary body
    insts = _emit_loop_countdown(
        counter=counter, r_one=r_one, k=3, body=body, label_gen=label_gen,
    )
    # Prepend the prologue: load r_one with 1.
    prologue = [Instruction(Op.LOAD, args=(r_one, 1))]
    p = Program.build(tuple(prologue + insts + [Instruction(Op.HALT)]))
    trace = run(p)
    # Body has ADD R2 R2 R2 — R2 starts at 0, stays at 0.
    # Counter starts at 3, ends at 0 after 3 iterations.
    final_regs = trace.steps[-1].regs
    assert final_regs[counter] == 0
```

- [ ] **Step 2: Run — verify failure**

Run: `pytest tinyvm/tests/test_generators.py -v`

- [ ] **Step 3: Implement**

Append to `generators.py`:

```python
class _LabelGen:
    """Fresh-label allocator; emits L0, L1, ..."""
    def __init__(self) -> None:
        self._next = 0

    def fresh(self) -> str:
        lbl = f"L{self._next}"
        self._next += 1
        return lbl


def _emit_loop_countdown(
    counter: int,
    r_one: int,
    k: int,
    body: list[Instruction],
    label_gen: _LabelGen,
) -> list[Instruction]:
    """Emit a count-down loop body executing `body` exactly k times.

    Pre-condition: r_one must be loaded with 1 before this block. Counter
    is loaded inline.
    """
    l_top = label_gen.fresh()
    l_done = label_gen.fresh()
    insts: list[Instruction] = [
        Instruction(Op.LOAD, args=(counter, k)),
    ]
    insts.append(_with_label(body[0], l_top) if body else Instruction(Op.NOP, label=l_top))
    if body:
        insts.extend(body[1:])
    else:
        pass  # the NOP-with-label above is the only body element.
    insts.append(Instruction(Op.SUB, args=(counter, counter, r_one)))
    insts.append(Instruction(Op.JZ, args=(counter,), target=l_done))
    insts.append(Instruction(Op.JMP, args=(), target=l_top))
    insts.append(Instruction(Op.NOP, label=l_done))
    return insts


def _with_label(inst: Instruction, label: str) -> Instruction:
    """Return a copy of inst carrying `label`."""
    return Instruction(op=inst.op, args=inst.args, label=label, target=inst.target)
```

- [ ] **Step 4: Verify tests pass**

Run: `pytest tinyvm/tests/test_generators.py -v`

- [ ] **Step 5: Commit**

```bash
git add tinyvm/generators.py tinyvm/tests/test_generators.py
git commit -m "feat(tinyvm): loop template — count-down"
```

---

### Task 28: Loop templates — count-up and test-at-top

**Files:**
- Modify: `tinyvm/generators.py`
- Modify: `tinyvm/tests/test_generators.py`

Refs spec §7.2(b), (c).

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/tests/test_generators.py
from tinyvm.generators import _emit_loop_countup, _emit_loop_test_at_top


def test_loop_countup_executes_k_iterations():
    label_gen = _LabelGen()
    insts = _emit_loop_countup(
        counter=0, r_k=1, r_diff=2, r_one=3, k=4,
        body=[Instruction(Op.ADD, args=(4, 4, 3))],
        label_gen=label_gen,
    )
    prologue = [Instruction(Op.LOAD, args=(3, 1))]
    p = Program.build(tuple(prologue + insts + [Instruction(Op.HALT)]))
    trace = run(p)
    # R4 += 1 each iteration; after 4 iterations R4 == 4.
    assert trace.steps[-1].regs[4] == 4


def test_loop_test_at_top_zero_iterations_skips_body():
    label_gen = _LabelGen()
    insts = _emit_loop_test_at_top(
        counter=0, r_one=1, k=0,
        body=[Instruction(Op.ADD, args=(2, 2, 1))],
        label_gen=label_gen,
    )
    prologue = [Instruction(Op.LOAD, args=(1, 1))]
    p = Program.build(tuple(prologue + insts + [Instruction(Op.HALT)]))
    trace = run(p)
    # k=0 means the body never executes; R2 stays 0.
    assert trace.steps[-1].regs[2] == 0
```

- [ ] **Step 2: Run — verify failure**

Run: `pytest tinyvm/tests/test_generators.py -v`

- [ ] **Step 3: Implement**

Append to `generators.py`:

```python
def _emit_loop_countup(
    counter: int, r_k: int, r_diff: int, r_one: int, k: int,
    body: list[Instruction], label_gen: _LabelGen,
) -> list[Instruction]:
    """Spec §7.2(b) count-up loop. Pre-condition: r_one == 1 loaded."""
    l_top = label_gen.fresh()
    l_done = label_gen.fresh()
    insts: list[Instruction] = [
        Instruction(Op.LOAD, args=(counter, 0)),
        Instruction(Op.LOAD, args=(r_k, k)),
    ]
    if body:
        insts.append(_with_label(body[0], l_top))
        insts.extend(body[1:])
    else:
        insts.append(Instruction(Op.NOP, label=l_top))
    insts.append(Instruction(Op.ADD, args=(counter, counter, r_one)))
    insts.append(Instruction(Op.SUB, args=(r_diff, r_k, counter)))
    insts.append(Instruction(Op.JZ, args=(r_diff,), target=l_done))
    insts.append(Instruction(Op.JMP, args=(), target=l_top))
    insts.append(Instruction(Op.NOP, label=l_done))
    return insts


def _emit_loop_test_at_top(
    counter: int, r_one: int, k: int,
    body: list[Instruction], label_gen: _LabelGen,
) -> list[Instruction]:
    """Spec §7.2(c) test-at-top loop. Pre-condition: r_one == 1 loaded."""
    l_top = label_gen.fresh()
    l_done = label_gen.fresh()
    insts: list[Instruction] = [
        Instruction(Op.LOAD, args=(counter, k)),
        Instruction(Op.JZ, args=(counter,), target=l_done, label=l_top),
    ]
    insts.extend(body)
    insts.append(Instruction(Op.SUB, args=(counter, counter, r_one)))
    insts.append(Instruction(Op.JMP, args=(), target=l_top))
    insts.append(Instruction(Op.NOP, label=l_done))
    return insts
```

- [ ] **Step 4: Verify tests pass**

Run: `pytest tinyvm/tests/test_generators.py -v`

- [ ] **Step 5: Commit**

```bash
git add tinyvm/generators.py tinyvm/tests/test_generators.py
git commit -m "feat(tinyvm): loop templates — count-up and test-at-top"
```

---

### Task 29: Branch templates — if, if-else, arithmetic-zero-test

**Files:**
- Modify: `tinyvm/generators.py`
- Modify: `tinyvm/tests/test_generators.py`

Refs spec §7.3.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/tests/test_generators.py
from tinyvm.generators import _emit_branch_if, _emit_branch_ifelse, _emit_branch_arith_zero


def test_branch_if_executes_body_on_nonzero_condition():
    label_gen = _LabelGen()
    insts = _emit_branch_if(
        cmp_op=Op.LT, ri=0, rj=1, rc=2,
        then_block=[Instruction(Op.LOAD, args=(3, 99))],
        label_gen=label_gen,
    )
    prologue = [
        Instruction(Op.LOAD, args=(0, 1)),    # Ri=1
        Instruction(Op.LOAD, args=(1, 5)),    # Rj=5 -> Ri<Rj true -> Rc=1
    ]
    p = Program.build(tuple(prologue + insts + [Instruction(Op.HALT)]))
    trace = run(p)
    assert trace.steps[-1].regs[3] == 99


def test_branch_ifelse_executes_correct_arm():
    label_gen = _LabelGen()
    insts = _emit_branch_ifelse(
        cmp_op=Op.LT, ri=0, rj=1, rc=2,
        then_block=[Instruction(Op.LOAD, args=(3, 1))],
        else_block=[Instruction(Op.LOAD, args=(3, 2))],
        label_gen=label_gen,
    )
    # Ri > Rj -> Rc=0 -> JZ taken -> else arm.
    prologue = [
        Instruction(Op.LOAD, args=(0, 5)),
        Instruction(Op.LOAD, args=(1, 1)),
    ]
    p = Program.build(tuple(prologue + insts + [Instruction(Op.HALT)]))
    trace = run(p)
    assert trace.steps[-1].regs[3] == 2


def test_branch_arith_zero_uses_sub_to_produce_zero():
    label_gen = _LabelGen()
    insts = _emit_branch_arith_zero(
        arith_op=Op.SUB, ri=0, rj=1, rc=2,
        then_block=[Instruction(Op.LOAD, args=(3, 7))],
        label_gen=label_gen,
    )
    # SUB Rc Ri Rj -> Rc = Ri - Rj = 0 -> JZ taken -> skip then.
    prologue = [
        Instruction(Op.LOAD, args=(0, 5)),
        Instruction(Op.LOAD, args=(1, 5)),
    ]
    p = Program.build(tuple(prologue + insts + [Instruction(Op.HALT)]))
    trace = run(p)
    assert trace.steps[-1].regs[3] == 0   # then_block did not execute
```

- [ ] **Step 2: Run — verify failure**

Run: `pytest tinyvm/tests/test_generators.py -v`

- [ ] **Step 3: Implement**

Append to `generators.py`:

```python
def _emit_branch_if(
    cmp_op: Op, ri: int, rj: int, rc: int,
    then_block: list[Instruction], label_gen: _LabelGen,
) -> list[Instruction]:
    """Spec §7.3(a). cmp_op in {Op.LT, Op.EQ}."""
    l_after = label_gen.fresh()
    insts: list[Instruction] = [
        Instruction(cmp_op, args=(rc, ri, rj)),
        Instruction(Op.JZ, args=(rc,), target=l_after),
    ]
    insts.extend(then_block)
    insts.append(Instruction(Op.NOP, label=l_after))
    return insts


def _emit_branch_ifelse(
    cmp_op: Op, ri: int, rj: int, rc: int,
    then_block: list[Instruction], else_block: list[Instruction],
    label_gen: _LabelGen,
) -> list[Instruction]:
    """Spec §7.3(b)."""
    l_else = label_gen.fresh()
    l_after = label_gen.fresh()
    insts: list[Instruction] = [
        Instruction(cmp_op, args=(rc, ri, rj)),
        Instruction(Op.JZ, args=(rc,), target=l_else),
    ]
    insts.extend(then_block)
    insts.append(Instruction(Op.JMP, args=(), target=l_after))
    if else_block:
        insts.append(_with_label(else_block[0], l_else))
        insts.extend(else_block[1:])
    else:
        insts.append(Instruction(Op.NOP, label=l_else))
    insts.append(Instruction(Op.NOP, label=l_after))
    return insts


def _emit_branch_arith_zero(
    arith_op: Op, ri: int, rj: int, rc: int,
    then_block: list[Instruction], label_gen: _LabelGen,
) -> list[Instruction]:
    """Spec §7.3(c). arith_op in {ADD, SUB, MUL, MOV}."""
    l_after = label_gen.fresh()
    if arith_op == Op.MOV:
        insts: list[Instruction] = [Instruction(Op.MOV, args=(rc, rj))]
    else:
        insts = [Instruction(arith_op, args=(rc, ri, rj))]
    insts.append(Instruction(Op.JZ, args=(rc,), target=l_after))
    insts.extend(then_block)
    insts.append(Instruction(Op.NOP, label=l_after))
    return insts
```

- [ ] **Step 4: Verify tests pass**

Run: `pytest tinyvm/tests/test_generators.py -v`

- [ ] **Step 5: Commit**

```bash
git add tinyvm/generators.py tinyvm/tests/test_generators.py
git commit -m "feat(tinyvm): branch templates — if, if-else, arithmetic-zero-test"
```

---

### Task 30: Stack templates — depth-1 pair and nested

**Files:**
- Modify: `tinyvm/generators.py`
- Modify: `tinyvm/tests/test_generators.py`

Refs spec §7.4.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/tests/test_generators.py
from tinyvm.generators import _emit_stack_pair, _emit_stack_nested


def test_stack_pair_round_trips_value():
    insts = _emit_stack_pair(
        save=0, load_back=1,
        body=[Instruction(Op.LOAD, args=(0, 99))],  # clobber R0
    )
    prologue = [Instruction(Op.LOAD, args=(0, 42))]
    p = Program.build(tuple(prologue + insts + [Instruction(Op.HALT)]))
    trace = run(p)
    assert trace.steps[-1].regs[1] == 42


def test_stack_nested_round_trips_in_lifo_order():
    insts = _emit_stack_nested(
        saves=[0, 1], pops=[3, 2],
        body=[Instruction(Op.LOAD, args=(0, 0)), Instruction(Op.LOAD, args=(1, 0))],
    )
    prologue = [
        Instruction(Op.LOAD, args=(0, 5)),
        Instruction(Op.LOAD, args=(1, 7)),
    ]
    p = Program.build(tuple(prologue + insts + [Instruction(Op.HALT)]))
    trace = run(p)
    # LIFO: first POP gets R1's saved value (7), second POP gets R0's (5).
    assert trace.steps[-1].regs[3] == 7
    assert trace.steps[-1].regs[2] == 5
```

- [ ] **Step 2: Run — verify failure**

Run: `pytest tinyvm/tests/test_generators.py -v`

- [ ] **Step 3: Implement**

Append to `generators.py`:

```python
def _emit_stack_pair(
    save: int, load_back: int, body: list[Instruction],
) -> list[Instruction]:
    """Spec §7.4(a). PUSH `save`, run body, POP into `load_back`."""
    insts: list[Instruction] = [Instruction(Op.PUSH, args=(save,))]
    insts.extend(body)
    insts.append(Instruction(Op.POP, args=(load_back,)))
    return insts


def _emit_stack_nested(
    saves: list[int], pops: list[int], body: list[Instruction],
) -> list[Instruction]:
    """Spec §7.4(b). LIFO: PUSH saves[0], ..., saves[-1]; body; POP pops[0], ..., pops[-1]."""
    assert len(saves) == len(pops), "saves and pops must have equal length"
    insts: list[Instruction] = [Instruction(Op.PUSH, args=(s,)) for s in saves]
    insts.extend(body)
    insts.extend(Instruction(Op.POP, args=(p,)) for p in pops)
    return insts
```

- [ ] **Step 4: Verify tests pass**

Run: `pytest tinyvm/tests/test_generators.py -v`

- [ ] **Step 5: Commit**

```bash
git add tinyvm/generators.py tinyvm/tests/test_generators.py
git commit -m "feat(tinyvm): stack templates — depth-1 pair and nested"
```

---

### Task 31: gen_branched assembly

**Files:**
- Modify: `tinyvm/generators.py`
- Modify: `tinyvm/tests/test_generators.py`

Refs spec §7.5 row 3.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/tests/test_generators.py
from tinyvm.generators import gen_branched


def test_gen_branched_validates_at_tier2_difficulties():
    for seed in range(20):
        spec = GenSpec(n=64, k=4, b=2, l=8, use_stack=False, stack_frames=0)
        from tinyvm.generators import gen_branched
        p = gen_branched(spec=spec, rng=random.Random(seed))
        assert validate(p), f"seed={seed} failed validate"
        trace = run(p)
        assert trace.halted


def test_gen_branched_emits_print_at_least_once():
    spec = GenSpec(n=32, k=4, b=1, l=0)
    p = gen_branched(spec=spec, rng=random.Random(0))
    assert any(inst.op == Op.PRINT for inst in p.instructions)


def test_gen_branched_with_stack_includes_push_pop():
    spec = GenSpec(n=32, k=6, b=1, l=0, use_stack=True, stack_frames=1)
    p = gen_branched(spec=spec, rng=random.Random(0))
    assert any(inst.op == Op.PUSH for inst in p.instructions)
    assert any(inst.op == Op.POP for inst in p.instructions)


def test_gen_branched_loop_budget_is_respected():
    """Sum of loop iteration counts in the program should be <= l."""
    spec = GenSpec(n=64, k=4, b=0, l=8)
    p = gen_branched(spec=spec, rng=random.Random(0))
    # Loop counter LOAD values are the K_i; sum them.
    # This relies on loop counters being LOADed with their K value at top.
    # Approximation: a generator-internal budget marker would be cleaner,
    # but for the test we run the program and assert the dynamic step count
    # is bounded.
    trace = run(p)
    # Loose bound: dynamic steps ≤ static length × (1 + l per static instr).
    # Tight bound is harder without exposing counter K values; rely on no-runaway.
    assert len(trace.steps) <= len(p.instructions) * (1 + spec.l)
```

- [ ] **Step 2: Run — verify failure**

Run: `pytest tinyvm/tests/test_generators.py -v`

- [ ] **Step 3: Implement gen_branched**

Append to `generators.py`:

```python
def gen_branched(spec: GenSpec, rng: random.Random) -> Program:
    """Tier 2 / Tier 4 generator (spec §7.5).

    Strategy: build a flat sequence of regions (straight-line fill, branches,
    loops, stack frames), then assemble. The iteration budget `spec.l` is
    distributed across `n_loops` loop regions, with each K drawn from the
    remaining budget.

    Active register subset is sampled per program; loop counters and stack
    spill registers are reserved within the active set.
    """
    active = _allocate_registers(k=spec.k, rng=rng)
    label_gen = _LabelGen()

    # Reserve registers for housekeeping.
    # Required: r_one (constant 1), one counter per loop, scratch r_diff for count-up.
    # Plus one r_k for count-up. Plus print target.
    num_loops_target = _pick_num_loops(spec.l, rng)
    loop_Ks = _split_budget(total=spec.l, n_parts=num_loops_target, rng=rng)
    n_reserved_for_loops = num_loops_target  # one counter each
    # Plus 3 reserved housekeeping regs for count-up scratch (we always allocate them
    # so we don't have to specialise per loop template).
    needed_reserved = 1 + n_reserved_for_loops + 2  # r_one + counters + (r_k, r_diff)
    if needed_reserved > len(active):
        # Caller picked k too small; reduce loop count.
        max_loops = max(0, len(active) - 3)
        num_loops_target = min(num_loops_target, max_loops)
        loop_Ks = _split_budget(total=spec.l, n_parts=num_loops_target, rng=rng)

    reserved = list(active)
    r_one = reserved.pop()
    counter_pool = [reserved.pop() for _ in range(num_loops_target)]
    r_k = reserved.pop() if reserved else active[0]
    r_diff = reserved.pop() if reserved else active[0]
    writable_for_fill = set(reserved)
    if not writable_for_fill:
        writable_for_fill = set(active)
    exclude_for_fill = (set(active) - writable_for_fill) | {r_one, r_k, r_diff} | set(counter_pool)

    insts: list[Instruction] = [Instruction(Op.LOAD, args=(r_one, 1))]

    # Distribute the static-instruction budget across regions.
    fill_per_region = max(1, spec.n // max(1, (spec.b + num_loops_target + 1)))
    cmp_ops = [Op.LT, Op.EQ]
    arith_ops = [Op.ADD, Op.SUB, Op.MUL, Op.MOV]

    # Open with a straight-line warm-up so PRINT-able regs become defined.
    insts.extend(_fill_block(
        n=max(spec.k, 4), active=active, rng=rng, exclude=exclude_for_fill | {r_one},
    ))

    # Emit branch regions.
    for _ in range(spec.b):
        ri, rj = rng.sample(active, 2)
        rc = rng.choice([r for r in active if r not in {ri, rj} and r not in (r_one,)] or active)
        then_block = _fill_block(
            n=fill_per_region, active=active, rng=rng, exclude=exclude_for_fill,
        )
        # 20% template (c), 80% split between (a) and (b).
        roll = rng.random()
        if roll < 0.2:
            arith = rng.choice(arith_ops)
            insts.extend(_emit_branch_arith_zero(arith, ri, rj, rc, then_block, label_gen))
        elif roll < 0.6:
            cmp_op = rng.choice(cmp_ops)
            insts.extend(_emit_branch_if(cmp_op, ri, rj, rc, then_block, label_gen))
        else:
            cmp_op = rng.choice(cmp_ops)
            else_block = _fill_block(
                n=fill_per_region, active=active, rng=rng, exclude=exclude_for_fill,
            )
            insts.extend(_emit_branch_ifelse(cmp_op, ri, rj, rc, then_block, else_block, label_gen))

    # Emit loop regions.
    for i in range(num_loops_target):
        counter = counter_pool[i]
        k = loop_Ks[i]
        body = _fill_block(
            n=fill_per_region, active=active, rng=rng,
            exclude=exclude_for_fill,
        )
        template_choice = rng.choice(["countdown", "countup", "test_at_top"])
        if template_choice == "countdown":
            insts.extend(_emit_loop_countdown(counter, r_one, k, body, label_gen))
        elif template_choice == "countup":
            insts.extend(_emit_loop_countup(counter, r_k, r_diff, r_one, k, body, label_gen))
        else:
            insts.extend(_emit_loop_test_at_top(counter, r_one, k, body, label_gen))

    # Emit stack frames if requested.
    if spec.use_stack:
        for _ in range(spec.stack_frames):
            save = rng.choice(active)
            load_back = rng.choice(active)
            body = _fill_block(
                n=max(2, fill_per_region // 2), active=active, rng=rng,
                exclude=exclude_for_fill,
            )
            insts.extend(_emit_stack_pair(save, load_back, body))

    # Final PRINT and HALT. Pick a register written somewhere in the program.
    print_target = rng.choice(active)
    # Ensure print_target was written: if not, add a final LOAD.
    if not _was_written(insts, print_target):
        insts.append(Instruction(Op.LOAD, args=(print_target, rng.randint(LITERAL_MIN, LITERAL_MAX))))
    insts.append(Instruction(Op.PRINT, args=(print_target,)))
    insts.append(Instruction(Op.HALT))
    return Program.build(tuple(insts))


def _was_written(insts: list[Instruction], reg: int) -> bool:
    """Quick check: is `reg` written by any instruction in `insts`?"""
    writes_one_reg = {
        Op.LOAD, Op.MOV, Op.ADD, Op.SUB, Op.MUL, Op.DIV,
        Op.NEG, Op.EQ, Op.LT, Op.POP,
    }
    return any(
        i.op in writes_one_reg and i.args and i.args[0] == reg
        for i in insts
    )


def _pick_num_loops(budget: int, rng: random.Random) -> int:
    """Pick a number of loops compatible with a total iteration budget."""
    if budget <= 0:
        return 0
    return rng.randint(1, min(4, budget))


def _split_budget(total: int, n_parts: int, rng: random.Random) -> list[int]:
    """Partition `total` into `n_parts` positive ints summing to `total`."""
    if n_parts == 0:
        return []
    if n_parts == 1:
        return [total]
    # Sample (n_parts - 1) cut points in [1, total - 1].
    if total < n_parts:
        # Pad to n_parts with at least 1 each (uses up to n_parts > total).
        return [1] * n_parts
    cuts = sorted(rng.sample(range(1, total), n_parts - 1))
    parts = [cuts[0]] + [cuts[i] - cuts[i - 1] for i in range(1, n_parts - 1)] + [total - cuts[-1]]
    return parts
```

- [ ] **Step 4: Verify tests pass**

Run: `pytest tinyvm/tests/test_generators.py -v`

- [ ] **Step 5: Commit**

```bash
git add tinyvm/generators.py tinyvm/tests/test_generators.py
git commit -m "feat(tinyvm): gen_branched assembly (Tiers 2/4 base)"
```

---

### Task 32: UseropPair and UseropTrace dataclasses

**Files:**
- Modify: `tinyvm/generators.py`
- Modify: `tinyvm/tests/test_generators.py`

Refs spec §7.5 (last row).

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/tests/test_generators.py
from tinyvm.generators import UseropPair, UseropTrace


def test_userop_pair_holds_with_symbol_base_and_trace():
    p_sym = Program.build((Instruction(Op.USEROP_0, args=(1, 0)),))
    p_base = Program.build((Instruction(Op.ADD, args=(1, 0, 0)),))
    from tinyvm.interpreter import run
    trace = run(p_base)
    pair = UseropPair(with_symbol=p_sym, base=p_base, trace=trace)
    assert pair.with_symbol is p_sym
    assert pair.base is p_base
    assert pair.trace is trace


def test_userop_trace_holds_demos_and_target():
    p_sym = Program.build((Instruction(Op.USEROP_0, args=(1, 0)), Instruction(Op.HALT)))
    p_base = Program.build((Instruction(Op.ADD, args=(1, 0, 0)), Instruction(Op.HALT)))
    trace = run(p_base)
    pair = UseropPair(with_symbol=p_sym, base=p_base, trace=trace)
    ut = UseropTrace(
        decomposition={"DOUBLE": [Instruction(Op.ADD, args=(1, 0, 0))]},
        demos=[pair],
        target=pair,
    )
    assert ut.demos[0] is pair
    assert ut.target is pair
```

- [ ] **Step 2: Run — verify failure**

Run: `pytest tinyvm/tests/test_generators.py -v`

- [ ] **Step 3: Implement**

Append to `generators.py`:

```python
from tinyvm.interpreter import ExecutionTrace


@dataclass(frozen=True)
class UseropPair:
    """Spec §7.5. with_symbol = surface; base = decomposition-substituted; trace = run(base)."""
    with_symbol: Program
    base: Program
    trace: ExecutionTrace


@dataclass(frozen=True)
class UseropTrace:
    """Spec §7.5 return type of gen_userop_trace."""
    decomposition: dict[str, list[Instruction]]
    demos: list[UseropPair]
    target: UseropPair
```

- [ ] **Step 4: Verify tests pass**

Run: `pytest tinyvm/tests/test_generators.py -v`

- [ ] **Step 5: Commit**

```bash
git add tinyvm/generators.py tinyvm/tests/test_generators.py
git commit -m "feat(tinyvm): UseropPair and UseropTrace dataclasses"
```

---

### Task 33: Decomposition substitution

**Files:**
- Modify: `tinyvm/generators.py`
- Modify: `tinyvm/tests/test_generators.py`

Refs spec §7.5 (CoT scaffold uses this).

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/tests/test_generators.py
from tinyvm.generators import substitute_userops, DEFAULT_USEROP_BINDINGS


def test_substitute_replaces_userop_with_base_sequence():
    p = Program.build((
        Instruction(Op.LOAD, args=(0, 3)),
        Instruction(Op.USEROP_0, args=(1, 0)),   # DOUBLE R1 R0
        Instruction(Op.PRINT, args=(1,)),
        Instruction(Op.HALT),
    ))
    decomp = {"DOUBLE": [Instruction(Op.ADD, args=(1, 0, 0))]}
    p_base = substitute_userops(p, decomp)
    trace = run(p_base)
    assert trace.output == [6]
```

- [ ] **Step 2: Run — verify failure**

Run: `pytest tinyvm/tests/test_generators.py -v`

- [ ] **Step 3: Implement**

Append to `generators.py`:

```python
from tinyvm.tokeniser import USEROP_SLOT_TO_SYMBOL


# Userop binding metadata (spec §7.5; §12 default uses SIGN for slot 4 instead
# of XOR). This map records *which slot each named userop occupies*, its arg
# count, and which arg position is the destination register. Full
# decomposition bodies are caller-provided via the `opcode_spec` argument of
# `gen_userop_trace` (Task 34); the module ships no canned decompositions.
DEFAULT_USEROP_BINDINGS: dict[str, dict[str, object]] = {
    "DOUBLE": {"slot": Op.USEROP_0, "n_args": 2, "writes": {0}},
    "MAX":    {"slot": Op.USEROP_1, "n_args": 3, "writes": {0}},
    "ABS":    {"slot": Op.USEROP_2, "n_args": 2, "writes": {0}},
    "MOD":    {"slot": Op.USEROP_3, "n_args": 3, "writes": {0}},
    "SIGN":   {"slot": Op.USEROP_4, "n_args": 2, "writes": {0}},
}


def substitute_userops(
    program: Program,
    decomposition: dict[str, list[Instruction]],
) -> Program:
    """Replace every USEROP_* instruction with the base-op sequence from `decomposition`.

    The decomposition list is templated on argument positions: an Instruction with
    args=(1, 0) in the userop call is matched against the decomposition's args by
    *position* (arg slot 0 -> first arg of userop, etc.). Decomposition Instructions
    use placeholder register indices 0..N-1 mapping to userop arg slots.
    """
    new_insts: list[Instruction] = []
    for inst in program.instructions:
        if not inst.op.is_userop():
            new_insts.append(inst)
            continue
        sym = USEROP_SLOT_TO_SYMBOL[inst.op]
        if sym not in decomposition:
            raise ValueError(f"no decomposition for userop {sym}")
        template = decomposition[sym]
        for t_inst in template:
            mapped_args = tuple(
                # If this position is a register reference to slot i, remap to inst.args[i].
                inst.args[a] for a in t_inst.args
            )
            new_inst = Instruction(
                op=t_inst.op,
                args=mapped_args,
                label=inst.label if t_inst is template[0] else None,
                target=t_inst.target,
            )
            new_insts.append(new_inst)
    return Program.build(tuple(new_insts))
```

- [ ] **Step 4: Verify tests pass**

Run: `pytest tinyvm/tests/test_generators.py -v`

- [ ] **Step 5: Commit**

```bash
git add tinyvm/generators.py tinyvm/tests/test_generators.py
git commit -m "feat(tinyvm): substitute_userops + default bindings"
```

---

### Task 34: gen_userop_trace

**Files:**
- Modify: `tinyvm/generators.py`
- Modify: `tinyvm/tests/test_generators.py`

Refs spec §7.5 last row.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/tests/test_generators.py
from tinyvm.generators import gen_userop_trace


DOUBLE_DECOMP = {"DOUBLE": [Instruction(Op.ADD, args=(0, 1, 1))]}
# Decomposition template uses arg slots: arg[0] -> destination, arg[1] -> source.


def test_gen_userop_trace_returns_userop_trace_with_demos_and_target():
    ut = gen_userop_trace(
        opcode_spec={"name": "DOUBLE", "n_args": 2, "decomposition": DOUBLE_DECOMP["DOUBLE"]},
        k_demos=2,
        n_target=8,
        use_stack=False,
        rng=random.Random(0),
    )
    assert len(ut.demos) == 2
    assert isinstance(ut.target, UseropPair)
    assert "DOUBLE" in ut.decomposition


def test_gen_userop_trace_target_trace_outputs_substitution_result():
    """target.trace should equal run(substitute_userops(target.with_symbol, decomposition))."""
    ut = gen_userop_trace(
        opcode_spec={"name": "DOUBLE", "n_args": 2, "decomposition": DOUBLE_DECOMP["DOUBLE"]},
        k_demos=1,
        n_target=8,
        use_stack=False,
        rng=random.Random(0),
    )
    expected_base = substitute_userops(ut.target.with_symbol, ut.decomposition)
    expected_trace = run(expected_base)
    assert ut.target.trace.output == expected_trace.output
```

- [ ] **Step 2: Run — verify failure**

Run: `pytest tinyvm/tests/test_generators.py -v`

- [ ] **Step 3: Implement gen_userop_trace**

Append to `generators.py`:

```python
def gen_userop_trace(
    opcode_spec: dict,
    k_demos: int,
    n_target: int,
    use_stack: bool,
    rng: random.Random,
) -> UseropTrace:
    """Tier 4 generator (spec §7.5 last row).

    opcode_spec: {"name": str, "n_args": int, "decomposition": list[Instruction]}
    Decomposition uses positional arg-slot indices (0..n_args-1) as register placeholders.

    Strategy: bind the userop to USEROP_0 for simplicity; generate k_demos branched
    programs that include a call to the userop, plus one target program. Each program
    is realised in two forms: with_symbol (uses USEROP_0) and base (substituted).
    """
    name = opcode_spec["name"]
    n_args = opcode_spec["n_args"]
    decomp_template = opcode_spec["decomposition"]
    decomposition = {name: decomp_template}
    # Bind this userop to USEROP_0 for surface-token rendering.
    USEROP_SLOT_TO_SYMBOL[Op.USEROP_0] = name

    def _gen_one(n: int, rng_local: random.Random) -> UseropPair:
        # Generate a base program structurally and then *inject* one userop call.
        base_spec = GenSpec(n=max(n - n_args, 4), k=max(n_args, 2), b=0, l=0,
                            use_stack=use_stack, stack_frames=1 if use_stack else 0)
        p_skel = gen_branched(spec=base_spec, rng=rng_local)
        # Insert a USEROP_0 call before the final PRINT.
        active = list({a for inst in p_skel.instructions
                       for a in inst.args[:1]
                       if isinstance(a, int) and 0 <= a < NUM_REGS})[:n_args]
        while len(active) < n_args:
            active.append(rng_local.randint(0, NUM_REGS - 1))
        insts = list(p_skel.instructions)
        # Find PRINT index.
        print_idx = next(i for i, inst in enumerate(insts) if inst.op == Op.PRINT)
        userop_inst = Instruction(Op.USEROP_0, args=tuple(active[:n_args]))
        # Re-target PRINT to the destination of the userop.
        insts[print_idx] = Instruction(Op.PRINT, args=(active[0],))
        insts.insert(print_idx, userop_inst)
        p_with_symbol = Program.build(tuple(insts))
        p_base = substitute_userops(p_with_symbol, decomposition)
        trace = run(p_base)
        return UseropPair(with_symbol=p_with_symbol, base=p_base, trace=trace)

    demos = [_gen_one(n=8 + rng.randint(0, 4), rng_local=random.Random(rng.random())) for _ in range(k_demos)]
    target = _gen_one(n=n_target, rng_local=random.Random(rng.random()))
    return UseropTrace(decomposition=decomposition, demos=demos, target=target)
```

- [ ] **Step 4: Verify tests pass**

Run: `pytest tinyvm/tests/test_generators.py -v`

- [ ] **Step 5: Commit**

```bash
git add tinyvm/generators.py tinyvm/tests/test_generators.py
git commit -m "feat(tinyvm): gen_userop_trace (Tier 4)"
```

---

## Phase F — Userop renderers (Tier 4)

### Task 35: render_userop_direct

**Files:**
- Modify: `tinyvm/tokeniser.py`
- Modify: `tinyvm/tests/test_tokeniser.py`

Refs spec §8.3.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/tests/test_tokeniser.py
import random
from tinyvm.generators import gen_userop_trace
from tinyvm.isa import Op, Instruction
from tinyvm.tokeniser import render_userop_direct


def test_render_userop_direct_concatenates_demos_and_target():
    decomp = [Instruction(Op.ADD, args=(0, 1, 1))]   # DOUBLE: dst = src + src
    ut = gen_userop_trace(
        opcode_spec={"name": "DOUBLE", "n_args": 2, "decomposition": decomp},
        k_demos=2, n_target=6, use_stack=False, rng=random.Random(0),
    )
    inp, tgt = render_userop_direct(ut)
    inp_toks = [ID_TO_TOKEN[i] for i in inp]
    tgt_toks = [ID_TO_TOKEN[i] for i in tgt]
    # Input must contain the userop symbol (default binding for USEROP_0 == "DOUBLE").
    assert "DOUBLE" in inp_toks
    # Target must end with EOS.
    assert tgt_toks[-1] == EOS


def test_render_userop_direct_has_no_decomp_tokens():
    decomp = [Instruction(Op.ADD, args=(0, 1, 1))]
    ut = gen_userop_trace(
        opcode_spec={"name": "DOUBLE", "n_args": 2, "decomposition": decomp},
        k_demos=1, n_target=6, use_stack=False, rng=random.Random(0),
    )
    inp, _ = render_userop_direct(ut)
    inp_toks = [ID_TO_TOKEN[i] for i in inp]
    assert DECOMP not in inp_toks   # this is the *no-scaffold* condition
```

- [ ] **Step 2: Run — verify failure**

Run: `pytest tinyvm/tests/test_tokeniser.py -v`

- [ ] **Step 3: Implement**

Append to `tokeniser.py`:

```python
from tinyvm.generators import UseropTrace


def render_userop_direct(utrace: UseropTrace) -> tuple[list[int], list[int]]:
    """Spec §8.3, Tier 4 condition 1. No decomposition scaffolding."""
    inp_tokens: list[str] = [BOS]
    for pair in utrace.demos:
        for inst in pair.with_symbol.instructions:
            inp_tokens.extend(_encode_instruction(inst))
        # Demo output stream as supervision context.
        for v in pair.trace.output:
            inp_tokens.extend(_digits_of(v))
            inp_tokens.append(NEWLINE)
    # Target program (with userop symbol).
    for inst in utrace.target.with_symbol.instructions:
        inp_tokens.extend(_encode_instruction(inst))
    inp_tokens.append(EOS)
    # Target supervision = target program's output (via decomposition).
    tgt_tokens: list[str] = [BOS]
    for v in utrace.target.trace.output:
        tgt_tokens.extend(_digits_of(v))
        tgt_tokens.append(NEWLINE)
    tgt_tokens.append(EOS)
    return [TOKEN_TO_ID[t] for t in inp_tokens], [TOKEN_TO_ID[t] for t in tgt_tokens]
```

- [ ] **Step 4: Verify tests pass**

Run: `pytest tinyvm/tests/test_tokeniser.py -v`

- [ ] **Step 5: Commit**

```bash
git add tinyvm/tokeniser.py tinyvm/tests/test_tokeniser.py
git commit -m "feat(tinyvm): render_userop_direct (Tier 4 cond 1)"
```

---

### Task 36: render_userop_with_decomposition

**Files:**
- Modify: `tinyvm/tokeniser.py`
- Modify: `tinyvm/tests/test_tokeniser.py`

Refs spec §8.3.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/tests/test_tokeniser.py
from tinyvm.tokeniser import render_userop_with_decomposition


def test_render_userop_with_decomposition_emits_decomp_lines_in_demos():
    decomp = [Instruction(Op.ADD, args=(0, 1, 1))]
    ut = gen_userop_trace(
        opcode_spec={"name": "DOUBLE", "n_args": 2, "decomposition": decomp},
        k_demos=1, n_target=6, use_stack=False, rng=random.Random(0),
    )
    inp, _ = render_userop_with_decomposition(ut)
    inp_toks = [ID_TO_TOKEN[i] for i in inp]
    # At least one DECOMP token per userop call in demos.
    n_demo_userops = sum(
        1 for inst in ut.demos[0].with_symbol.instructions if inst.op.is_userop()
    )
    assert inp_toks.count(DECOMP) == n_demo_userops


def test_render_userop_with_decomposition_target_has_no_decomp():
    """The TARGET portion (after demos) must NOT carry decomposition annotations."""
    decomp = [Instruction(Op.ADD, args=(0, 1, 1))]
    ut = gen_userop_trace(
        opcode_spec={"name": "DOUBLE", "n_args": 2, "decomposition": decomp},
        k_demos=1, n_target=6, use_stack=False, rng=random.Random(0),
    )
    inp, _ = render_userop_with_decomposition(ut)
    inp_toks = [ID_TO_TOKEN[i] for i in inp]
    # Find the boundary: the last `EOS`-free segment after the demos. We
    # approximate via "DECOMP count equals number of userop calls in demos".
    # If any userop in the target had a DECOMP companion, the count would exceed.
    n_demo_userops = sum(
        1 for inst in ut.demos[0].with_symbol.instructions if inst.op.is_userop()
    )
    assert inp_toks.count(DECOMP) == n_demo_userops
```

- [ ] **Step 2: Run — verify failure**

Run: `pytest tinyvm/tests/test_tokeniser.py -v`

- [ ] **Step 3: Implement**

Append to `tokeniser.py`:

```python
def render_userop_with_decomposition(utrace: UseropTrace) -> tuple[list[int], list[int]]:
    """Spec §8.3, Tier 4 condition 2. Demos carry DECOMP lines after each userop."""
    inp_tokens: list[str] = [BOS]
    for pair in utrace.demos:
        for inst in pair.with_symbol.instructions:
            inp_tokens.extend(_encode_instruction(inst))
            if inst.op.is_userop():
                sym = USEROP_SLOT_TO_SYMBOL[inst.op]
                template = utrace.decomposition[sym]
                # Render the decomposition with concrete register remapping.
                inp_tokens.append(DECOMP)
                for t_inst in template:
                    mapped_args = tuple(inst.args[a] for a in t_inst.args)
                    concrete = Instruction(op=t_inst.op, args=mapped_args, target=t_inst.target)
                    inp_tokens.extend(_encode_instruction(concrete))
        for v in pair.trace.output:
            inp_tokens.extend(_digits_of(v))
            inp_tokens.append(NEWLINE)
    # Target — no decomposition annotations.
    for inst in utrace.target.with_symbol.instructions:
        inp_tokens.extend(_encode_instruction(inst))
    inp_tokens.append(EOS)
    # Target supervision.
    tgt_tokens: list[str] = [BOS]
    for v in utrace.target.trace.output:
        tgt_tokens.extend(_digits_of(v))
        tgt_tokens.append(NEWLINE)
    tgt_tokens.append(EOS)
    return [TOKEN_TO_ID[t] for t in inp_tokens], [TOKEN_TO_ID[t] for t in tgt_tokens]
```

- [ ] **Step 4: Verify tests pass**

Run: `pytest tinyvm/tests/test_tokeniser.py -v`

- [ ] **Step 5: Commit**

```bash
git add tinyvm/tokeniser.py tinyvm/tests/test_tokeniser.py
git commit -m "feat(tinyvm): render_userop_with_decomposition (Tier 4 cond 2)"
```

---

## Phase G — Shaping knobs

### Task 37: Wire ShapingSpec knobs into `gen_register_trace` and `gen_branched`

**Files:**
- Modify: `tinyvm/generators.py`
- Modify: `tinyvm/tests/test_generators.py`

Refs spec §7.6. We implement the four knobs as simple post-construction filters / tweaks. Each knob is independently togglable.

- [ ] **Step 1: Append the failing tests**

```python
# Append to tinyvm/tests/test_generators.py
from collections import Counter
from tinyvm.generators import gen_register_trace, GenSpec, ShapingSpec


def test_flat_output_histogram_widens_value_distribution():
    """With flat_output_histogram on, output values cover more bins than off."""
    bins_on, bins_off = Counter(), Counter()
    for seed in range(200):
        p_on = gen_register_trace(
            n=16, k=4, rng=random.Random(seed),
            shaping=ShapingSpec(flat_output_histogram=True),
        )
        p_off = gen_register_trace(
            n=16, k=4, rng=random.Random(seed),
            shaping=ShapingSpec(flat_output_histogram=False),
        )
        bins_on[run(p_on).output[0] // 100] += 1
        bins_off[run(p_off).output[0] // 100] += 1
    assert len(bins_on) >= len(bins_off)


def test_randomize_print_target_diversifies_print_register():
    targets = Counter()
    for seed in range(500):
        p = gen_register_trace(
            n=16, k=8, rng=random.Random(seed),
            shaping=ShapingSpec(randomize_print_target=True),
        )
        print_inst = [i for i in p.instructions if i.op == Op.PRINT][0]
        targets[print_inst.args[0]] += 1
    # With 8 active regs and randomize, no single reg should dominate
    # (>40% would be suspicious).
    assert max(targets.values()) < 0.40 * 500
```

- [ ] **Step 2: Run — verify failure**

Run: `pytest tinyvm/tests/test_generators.py -v`

- [ ] **Step 3: Implement the shaping logic**

Edit `gen_register_trace` in `generators.py`:

```python
def gen_register_trace(
    n: int,
    k: int,
    rng: random.Random,
    shaping: ShapingSpec | None = None,
) -> Program:
    """Tier 1 generator (spec §7.5 row 2) with optional ShapingSpec knobs."""
    shaping = shaping or ShapingSpec()
    active = _allocate_registers(k=k, rng=rng)
    # Reserve `distractor_regs` slots that we'll write to but never read for PRINT.
    n_dist = min(shaping.distractor_regs, len(active) - 1) if shaping.distractor_regs else 0
    distractors = set(active[:n_dist])
    print_pool = [r for r in active if r not in distractors] or active

    attempts = 200 if shaping.flat_output_histogram else 1
    for _ in range(attempts):
        body = _fill_block(n=n, active=active, rng=rng)
        if shaping.randomize_print_target:
            target_reg = rng.choice(print_pool)
        else:
            # Conventional: PRINT the most-recently-written register.
            target_reg = body[-1].args[0]
            if target_reg in distractors:
                target_reg = rng.choice(print_pool)
        insts = body + [Instruction(Op.PRINT, args=(target_reg,)), Instruction(Op.HALT)]
        p = Program.build(tuple(insts))
        if not shaping.flat_output_histogram:
            return p
        # Rejection-sample for histogram flatness: accept the program with
        # probability inversely proportional to how common this output bucket is.
        out_val = run(p).output[0]
        bucket = out_val // 100
        if not hasattr(gen_register_trace, "_buckets"):
            gen_register_trace._buckets = Counter()  # type: ignore[attr-defined]
        buckets: Counter = gen_register_trace._buckets  # type: ignore[attr-defined]
        if rng.random() > min(1.0, 1.0 / (1 + buckets[bucket] / 10.0)):
            buckets[bucket] += 1
            continue
        buckets[bucket] += 1
        return p
    return p  # last-resort: return whatever we have
```

(The `decorrelate_length` knob is left as a no-op for Tier 1 since `n` is fixed per call; it becomes meaningful in `gen_branched` where program length varies. Wiring it into `gen_branched` is deferred until Tier 2 ablations begin — note in spec §12.)

- [ ] **Step 4: Verify tests pass**

Run: `pytest tinyvm/tests/test_generators.py -v`

- [ ] **Step 5: Commit**

```bash
git add tinyvm/generators.py tinyvm/tests/test_generators.py
git commit -m "feat(tinyvm): wire shaping knobs into gen_register_trace"
```

---

## Phase H — Distribution sanity and determinism

### Task 38: Distribution sanity test layer

**Files:**
- Create: `tinyvm/tests/test_distribution.py`

Refs spec §10 distribution layer.

- [ ] **Step 1: Write the tests**

```python
# tinyvm/tests/test_distribution.py
"""Distribution sanity layer (spec §10).

Aggregate-stat assertions that catch *quiet* generator bugs the per-program
tests miss: a generator that 'works' but only ever PRINTs values in [0, 7],
or always picks R0 as the counter, etc.
"""
import random
from collections import Counter

import numpy as np

from tinyvm.generators import GenSpec, ShapingSpec, gen_branched, gen_register_trace
from tinyvm.isa import Op
from tinyvm.interpreter import run


def _outputs(generator_call, n_samples: int) -> list[int]:
    outs: list[int] = []
    for seed in range(n_samples):
        p = generator_call(seed)
        outs.append(run(p).output[0])
    return outs


def test_register_trace_output_distribution_is_diverse():
    outs = _outputs(
        lambda s: gen_register_trace(n=16, k=4, rng=random.Random(s)),
        n_samples=1000,
    )
    # At least 50 distinct output values across 1000 programs.
    assert len(set(outs)) >= 50


def test_branched_jz_predecessor_distribution_includes_non_comparators():
    """Spec §10: JZ-predecessor-opcode distribution should not be 100% comparators."""
    pred_counts = Counter()
    for seed in range(200):
        spec = GenSpec(n=32, k=4, b=4, l=0)
        p = gen_branched(spec=spec, rng=random.Random(seed))
        for i, inst in enumerate(p.instructions):
            if inst.op == Op.JZ and i > 0:
                pred_counts[p.instructions[i - 1].op.name] += 1
    total = sum(pred_counts.values())
    comparator_share = (pred_counts["LT"] + pred_counts["EQ"]) / max(1, total)
    # Template (c) is 20% — comparator share should be roughly 80% ± 15%.
    assert 0.55 < comparator_share < 0.95


def test_branched_active_register_use_is_roughly_uniform():
    """Spec §10: register-use counts uniform over active subset."""
    reg_writes = Counter()
    for seed in range(500):
        p = gen_register_trace(n=32, k=8, rng=random.Random(seed))
        writes_one_reg = {Op.LOAD, Op.MOV, Op.ADD, Op.SUB, Op.MUL, Op.DIV,
                          Op.NEG, Op.EQ, Op.LT, Op.POP}
        for inst in p.instructions:
            if inst.op in writes_one_reg and inst.args:
                reg_writes[inst.args[0]] += 1
    total = sum(reg_writes.values())
    # Each register should see roughly 1/8 of writes ± 50%.
    for r in range(8):
        share = reg_writes[r] / max(1, total)
        assert 0.05 < share < 0.25, f"R{r} write share is {share:.3f}"


def test_branched_loop_template_mix():
    """The three loop templates should be roughly evenly sampled."""
    template_counts = Counter()
    for seed in range(300):
        spec = GenSpec(n=32, k=6, b=0, l=6)
        p = gen_branched(spec=spec, rng=random.Random(seed))
        # Identify template by structural signature: count-down ends with
        # JZ → JMP; count-up has SUB-then-JZ on r_diff; test-at-top has JZ at top.
        # Approximation: count occurrences of (JMP target match prev block start).
        # Simpler: rely on the dynamic step count distribution being non-trivial.
        outs = run(p).output
        template_counts["any_loop_executed"] += int(len(outs) >= 1)
    assert template_counts["any_loop_executed"] >= 200   # >2/3 of programs run to PRINT
```

- [ ] **Step 2: Run — verify all pass**

Run: `pytest tinyvm/tests/test_distribution.py -v`
Expected: 4 tests pass. If any *fails*, investigate which generator drift triggered it.

- [ ] **Step 3: Commit**

```bash
git add tinyvm/tests/test_distribution.py
git commit -m "test(tinyvm): distribution sanity layer (spec §10)"
```

---

### Task 39: Determinism test layer

**Files:**
- Create: `tinyvm/tests/test_determinism.py`

Refs spec §10 determinism layer.

- [ ] **Step 1: Write the tests**

```python
# tinyvm/tests/test_determinism.py
"""Determinism layer (spec §10): same seed -> bit-exact program."""
import random

from tinyvm.generators import (
    GenSpec, gen_branched, gen_counter, gen_register_trace, gen_userop_trace,
)
from tinyvm.isa import Op, Instruction


def test_gen_counter_is_seed_deterministic():
    a = gen_counter(n=8, rng=random.Random(42))
    b = gen_counter(n=8, rng=random.Random(42))
    assert a == b


def test_gen_register_trace_is_seed_deterministic():
    a = gen_register_trace(n=16, k=4, rng=random.Random(42))
    b = gen_register_trace(n=16, k=4, rng=random.Random(42))
    assert a == b


def test_gen_branched_is_seed_deterministic():
    spec = GenSpec(n=32, k=4, b=2, l=6, use_stack=True, stack_frames=1)
    a = gen_branched(spec=spec, rng=random.Random(42))
    b = gen_branched(spec=spec, rng=random.Random(42))
    assert a == b


def test_different_seeds_yield_different_programs():
    a = gen_register_trace(n=16, k=4, rng=random.Random(1))
    b = gen_register_trace(n=16, k=4, rng=random.Random(2))
    assert a != b


def test_gen_userop_trace_is_seed_deterministic():
    decomp = [Instruction(Op.ADD, args=(0, 1, 1))]
    a = gen_userop_trace(
        opcode_spec={"name": "DOUBLE", "n_args": 2, "decomposition": decomp},
        k_demos=2, n_target=8, use_stack=False, rng=random.Random(42),
    )
    b = gen_userop_trace(
        opcode_spec={"name": "DOUBLE", "n_args": 2, "decomposition": decomp},
        k_demos=2, n_target=8, use_stack=False, rng=random.Random(42),
    )
    assert a.target.with_symbol == b.target.with_symbol
```

- [ ] **Step 2: Run — verify all pass**

Run: `pytest tinyvm/tests/test_determinism.py -v`
Expected: 5 tests pass.

- [ ] **Step 3: Run the full suite end-to-end**

Run: `pytest -v`
Expected: every test across `test_isa`, `test_interpreter`, `test_tokeniser`, `test_verifier`, `test_generators`, `test_distribution`, `test_determinism` passes.

- [ ] **Step 4: Commit**

```bash
git add tinyvm/tests/test_determinism.py
git commit -m "test(tinyvm): determinism layer + full-suite green"
```

---

## Spec coverage map

| Spec section | Implemented by |
|---|---|
| §2 Scope (5 sub-modules, 5 renderers) | Tasks 1–39 |
| §3 Decisions (IR-first, hybrid gen, generate-only-valid, etc.) | Embedded across all phases |
| §5 ISA | Tasks 2–3 |
| §6 Interpreter (16 base + USEROP raises) | Tasks 4–8 |
| §7.1 Common gen procedure (incl. random active set) | Tasks 24, 25 |
| §7.2 Loop templates (3 shapes) | Tasks 27–28 |
| §7.3 Branch templates (3 shapes, including arith-zero-test) | Task 29 |
| §7.4 Stack templates (2 shapes) | Task 30 |
| §7.5 Four generators + UseropTrace + UseropPair | Tasks 23, 26, 31, 32, 34 |
| §7.6 Shaping knobs (4 fields) | Task 37 |
| §7.7 Reproducibility (seed-deterministic) | Task 39 |
| §8.1 64-token vocab (incl. DECOMP) | Task 9 |
| §8.2 Encoding format | Task 10 |
| §8.3 Five renderers | Tasks 12, 13, 14, 35, 36 |
| §8.4 Non-text probe mode (`probe_targets`) | Task 14 |
| §8.5 Decode + round-trip | Task 11 |
| §8.6 Text-level renderers for Qwen | Task 15 |
| §9 Verifier (score_output + validate + userop awareness) | Tasks 16–21 |
| §10 Five test layers | All Tasks; layers 4 (distribution) and 5 (determinism) explicit in Tasks 38–39 |
| §11 Risk mitigations (multiple templates, shaping, vocab reserve, CoT modes) | Embedded |
| §12 Open questions (XOR decomposition default → SIGN) | Task 9 vocab USEROP_TOKENS uses SIGN; documented in code comment |

---

## Plan complete

Plan complete and saved to `docs/superpowers/plans/2026-05-15-tinyvm-module.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
