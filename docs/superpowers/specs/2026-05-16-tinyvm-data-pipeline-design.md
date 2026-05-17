# Tiny-VM Data Pipeline — Design Spec

**Date:** 2026-05-16
**Authors:** Siddhant (@sidgraph), Claude (@claudeai)
**Status:** Approved for implementation planning
**Source:** `Latent_State_as_Computer.docx` §11 (Datasets), §17 Day 3 (Data pipeline); `docs/superpowers/specs/2026-05-15-tinyvm-module-design.md` (which deferred this work as out of scope)

## 1. Purpose

The Tiny-VM module shipped on PR #1 generates programs in memory. This spec covers the **Day 3 data pipeline**: materialise the per-tier datasets to disk as JSONL files at the sizes specified in parent §11.2, so the Day 4+ training scripts can load them with a simple `for row in load_jsonl(path)` loop.

The pipeline is single-process, Python-only, parameterised by a Python config module, and produces lossless rich-IR rows that also carry pre-rendered training prompts.

## 2. Scope

In scope:

- **`tinyvm/data/schema.py`** — JSONL row schema + serialise/deserialise.
- **`tinyvm/data/configs.py`** — `DatasetConfig` dataclass + `TIER0`, `TIER1`, `TIER2` instances + `CONFIGS` dict.
- **`tinyvm/data/emit.py`** — `emit(config, out_dir, seed_base) -> Path` writing JSONL + `manifest.json`.
- **`tinyvm/data/load.py`** — streaming reader + `load_prompts` fast path for training.
- **`tinyvm/data/__main__.py`** — CLI: `python -m tinyvm.data emit --tier tier1 --out data/` and `verify`.
- **Test suite** — schema round-trip, config sanity, emit correctness, load round-trip, byte-exact determinism, integration trace-replay.

Out of scope (deferred):

- **Tier 4 emission.** `gen_userop_trace` produces a `UseropTrace` (demos + target) which doesn't fit a single-`Program`-per-row model. Needs its own row variant; lands as a follow-up. The `configs.py` carries a `# TODO: Tier 4` marker.
- **Multi-process generation.** Single-process is acceptable for Day 3 (worst case ~2–4 h to emit Tier 2 once). Future `--workers N` flag.
- **HuggingFace `Dataset` wrapper.** `load_jsonl` returns an iterator; a HF `Dataset.from_generator` adapter is one line at the call site if/when needed.
- **Distributed / sharded loading.** Single file per (tier, split, bucket) is the layout.

## 3. Key design decisions

| # | Decision | Rationale |
|---|---|---|
| 1 | **Rich IR per row** — every row carries the full `Program` (list of instruction dicts) and `ExecutionTrace` (per-step register snapshots + output stream + halted flag). | Lossless; any future render mode can be computed from a row without re-running the generator. Storage cost (~3 KB/row at Tier 2) is acceptable. |
| 2 | **Pre-render training prompts at emit time.** Per-tier `renders: tuple[str, ...]` specifies which render modes are populated per row, each with `input_ids` + `target_ids` (custom 64-vocab) + `input_text` + `target_text` (Qwen-ready surface text). | Row is immediately training-ready and inspectable by eye; no train-time tokeniser dependency. Token IDs and text are both cheap to materialise and downstream code picks whichever it needs. |
| 3 | **Hybrid file layout** — flat `train.jsonl` per tier, stratified `eval/<bucket>.jsonl` per bucket. | Eval is consumed per-bucket (accuracy by length, etc.); train is consumed end-to-end. Matches the consumption pattern. |
| 4 | **Python config module** — `configs.py` holds `DatasetConfig` literals named `TIER0`, `TIER1`, `TIER2`. CLI/library reference by name. | Type-checked, IDE-friendly, recipe changes are diff-clear in PR review. No YAML schema layer. |
| 5 | **Single-process emit** with a future `--workers N` extension point. | Day 3 scope discipline; Tier 2 worst case ~2–4 h is tolerable for a one-shot. Parallelism is a bounded follow-up commit, not blocking. |
| 6 | **Deterministic per-row seeds via SHA-256 of `(seed_base, split, bucket, index)`.** | Bit-exact reproducibility across runs; no train/eval leakage; each row independently re-derivable from its stored `meta.seed`. |
| 7 | **Manifest file** (`manifest.json`) is written **last** with per-file SHA-256 + row counts + code version. | "Manifest present" means "emit completed". `verify` subcommand re-hashes and compares — a cheap CI gate against dataset drift. |
| 8 | **Op enum serialised by name** (string), not int value. | Human-readable when eyeballing rows; robust against any future Op enum reordering. |

## 4. Module structure

```
tinyvm/data/
├── __init__.py           # public re-exports (DatasetConfig, EvalBucket, Row, emit, load_jsonl, load_prompts, CONFIGS)
├── schema.py             # ~110 LOC — RowMeta dataclass, to_row, from_row, Row NamedTuple
├── configs.py            # ~130 LOC — DatasetConfig, EvalBucket, TIER0/TIER1/TIER2, CONFIGS dict
├── emit.py               # ~130 LOC — emit(), _emit_split, _build_renders, _row_seed, manifest writer
├── load.py               # ~70 LOC  — load_jsonl, load_split, load_prompts, load_manifest
└── __main__.py           # ~50 LOC  — argparse CLI with emit + verify subcommands
tinyvm/data/tests/
├── __init__.py
├── test_schema.py        # ~70 LOC  — round-trip serialise/deserialise property
├── test_configs.py       # ~50 LOC  — every config builds + validates
├── test_emit.py          # ~80 LOC  — emit small datasets, check structure + manifest
├── test_load.py          # ~50 LOC  — round-trip emit→load preserves everything
└── test_pipeline.py      # ~50 LOC  — determinism + integration (replay trace from loaded IR)
```

Total: ~490 LOC implementation + ~300 LOC tests = **~790 LOC**.

**File-by-file responsibility:**

- `schema.py` — the only file that knows the JSON layout. Adding a new field is a one-file change.
- `configs.py` — data, not logic. `DatasetConfig` literals only. Recipe changes are diff-clear.
- `emit.py` — the only file that opens output files and writes. Testable by pointing at `tmp_path`.
- `load.py` — pure decoder. Inverse of emit; the round-trip property test ties the two together.
- `__main__.py` — thin argparse wrapper; the library functions do all the work.

## 5. Schema (`schema.py`)

### 5.1 Row layout (verbatim example)

```json
{
  "meta": {
    "tier": "tier2",
    "split": "train",
    "bucket": null,
    "seed": 1234567,
    "axes": {"n": 64, "k": 4, "b": 2, "l": 8, "use_stack": false, "stack_frames": 0},
    "renders": ["direct", "cot"]
  },
  "program": [
    {"op": "LOAD", "args": [0, 5], "label": null, "target": null},
    {"op": "ADD",  "args": [1, 0, 0], "label": null, "target": null},
    {"op": "PRINT","args": [1], "label": null, "target": null},
    {"op": "HALT", "args": [],  "label": null, "target": null}
  ],
  "trace": {
    "steps": [
      {"pc": 0, "regs": [5, 0, 0, 0, 0, 0, 0, 0], "stack": [], "emitted": null},
      {"pc": 1, "regs": [5, 10, 0, 0, 0, 0, 0, 0], "stack": [], "emitted": null},
      {"pc": 2, "regs": [5, 10, 0, 0, 0, 0, 0, 0], "stack": [], "emitted": 10},
      {"pc": 3, "regs": [5, 10, 0, 0, 0, 0, 0, 0], "stack": [], "emitted": null}
    ],
    "output": [10],
    "halted": true
  },
  "renders": {
    "direct": {
      "input_ids":   [55, 0, 1, 41, 5, 41, 8, 0, 0, 0, 41, 13, 1, 41, 15, 41, 56],
      "target_ids":  [55, 39, 1, 0, 41, 56],
      "input_text":  "BOS LOAD R0 5\nADD R1 R0 R0\nPRINT R1\nHALT\nEOS",
      "target_text": "BOS 1 0\nEOS"
    },
    "cot": {
      "input_ids":   [...],
      "target_ids":  [...],
      "input_text":  "BOS LOAD R0 5\nADD R1 R0 R0\nPRINT R1\nHALT\nEOS",
      "target_text": "BOS LOAD R0 5\nR0=5R1=0R2=0R3=0R4=0R5=0R6=0R7=0\n...\n1 0\nEOS"
    }
  }
}
```

### 5.2 Dataclasses and API

```python
@dataclass(frozen=True)
class RowMeta:
    tier: str                          # "tier0" | "tier1" | "tier2"
    split: str                         # "train" | "eval"
    bucket: str | None                 # "len_64" for eval; None for train
    seed: int                          # row-specific seed used to derive the program
    axes: dict[str, int | bool]        # axis dial values at generation time
    renders: tuple[str, ...]           # render modes populated in this row, e.g. ("direct", "cot")


class Row(NamedTuple):
    program: Program
    trace: ExecutionTrace
    meta: RowMeta
    renders: dict[str, RenderedPrompt] # mode -> rendered prompt block


@dataclass(frozen=True)
class RenderedPrompt:
    input_ids: list[int]               # custom 64-vocab token IDs
    target_ids: list[int]
    input_text: str                    # Qwen-ready surface text
    target_text: str


def to_row(program: Program, trace: ExecutionTrace, meta: RowMeta,
           renders: dict[str, RenderedPrompt]) -> dict:
    """Serialise to a JSON-able dict. Pure function; no I/O."""

def from_row(row: dict) -> Row:
    """Inverse of to_row. Reconstructs Program, ExecutionTrace, RowMeta, renders dict."""
```

### 5.3 Round-trip invariant

The central correctness test:

```python
def test_round_trip_preserves_everything():
    p = gen_register_trace(n=16, k=4, rng=Random(0))
    trace = run(p)
    renders = _build_renders(p, trace, ("direct",))
    meta = RowMeta(tier="tier1", split="train", bucket=None, seed=42,
                   axes={"n": 16, "k": 4}, renders=("direct",))
    row = to_row(p, trace, meta, renders)
    out = from_row(row)
    assert out.program == p
    assert out.trace.output == trace.output
    assert out.trace.steps == trace.steps
    assert out.meta == meta
    assert out.renders == renders
```

### 5.4 Op serialisation

`Op` is serialised by `.name` (string), not by `.value` (int). The deserialiser uses `Op[name]`. Userop slots round-trip as `"USEROP_0"` etc.; their symbolic name (`"DOUBLE"`, etc.) is recoverable from `meta.axes` if needed for Tier 4 data later.

## 6. Configs (`configs.py`)

### 6.1 Dataclasses

```python
@dataclass(frozen=True)
class EvalBucket:
    name: str                          # filename-safe; becomes `eval/<name>.jsonl`
    size: int                          # number of programs in this bucket
    fixed_axes: dict[str, int | bool]  # exact axis values for every row


TrainAxesSampler = Callable[[random.Random], dict[str, int | bool]]
ProgramBuilder   = Callable[[random.Random, dict], Program]


@dataclass(frozen=True)
class DatasetConfig:
    tier: str
    train_size: int
    train_axes: TrainAxesSampler        # samples per-row axes for the train split
    eval_buckets: tuple[EvalBucket, ...]
    build: ProgramBuilder               # (rng, axes) -> Program — unifies the per-tier generator signatures
    renders: tuple[str, ...]            # render modes to emit per row
```

The `build` callable is the unifier across the three different generator signatures (`gen_counter(n, rng)`, `gen_register_trace(n, k, rng)`, `gen_branched(spec, rng)`). Each tier defines a small `_tierN_build(rng, axes) -> Program` shim and the emit loop is generator-agnostic.

### 6.2 Per-tier configs

```python
# ---- Tier 0 ----
def _tier0_train_axes(rng):
    return {"n": rng.randint(4, 8)}                  # parent §3.2 Tier 0 length axis

def _tier0_build(rng, axes):
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
def _tier1_train_axes(rng):
    return {"n": rng.randint(8, 32), "k": rng.choice([2, 4, 8])}

def _tier1_build(rng, axes):
    return gen_register_trace(n=axes["n"], k=axes["k"], rng=rng)

TIER1 = DatasetConfig(
    tier="tier1",
    train_size=200_000,
    train_axes=_tier1_train_axes,
    eval_buckets=tuple(
        EvalBucket(name=f"len_{n}", size=20_000, fixed_axes={"n": n, "k": 4})
        for n in (8, 16, 32, 48, 64, 96, 128)         # parent §6: in-dist 8-32, OOD 48-128
    ),
    build=_tier1_build,
    renders=("direct",),
)

# ---- Tier 2 ----
def _tier2_train_axes(rng):
    return {
        "n": rng.randint(16, 256),
        "k": rng.choice([4, 6, 8]),
        "b": rng.randint(1, 8),
        "l": rng.randint(0, 16),
        "use_stack": rng.random() < 0.5,
        "stack_frames": rng.randint(0, 2),
    }

def _tier2_build(rng, axes):
    return gen_branched(
        spec=GenSpec(
            n=axes["n"], k=axes["k"], b=axes["b"], l=axes["l"],
            use_stack=axes["use_stack"], stack_frames=axes["stack_frames"],
        ),
        rng=rng,
    )

TIER2 = DatasetConfig(
    tier="tier2",
    train_size=500_000,
    train_axes=_tier2_train_axes,
    eval_buckets=(
        EvalBucket(name="easy",        size=10_000, fixed_axes={"n":  32, "k": 4, "b": 1, "l": 0,  "use_stack": False, "stack_frames": 0}),
        EvalBucket(name="medium",      size=10_000, fixed_axes={"n":  64, "k": 4, "b": 2, "l": 4,  "use_stack": False, "stack_frames": 0}),
        EvalBucket(name="hard",        size=10_000, fixed_axes={"n": 128, "k": 6, "b": 4, "l": 8,  "use_stack": True,  "stack_frames": 1}),
        EvalBucket(name="ood_len_256", size=10_000, fixed_axes={"n": 256, "k": 4, "b": 2, "l": 4,  "use_stack": False, "stack_frames": 0}),
    ),
    build=_tier2_build,
    renders=("direct", "cot"),                       # parent §7.1 trains both conditions
)

# TODO Tier 4: `gen_userop_trace` returns UseropTrace (demos + target), not a single Program.
# Needs a row-variant schema. Defer to follow-up.

CONFIGS: dict[str, DatasetConfig] = {"tier0": TIER0, "tier1": TIER1, "tier2": TIER2}
```

## 7. Emit (`emit.py`)

### 7.1 Public API

```python
def emit(config: DatasetConfig, out_dir: Path, seed_base: int = 0) -> Path:
    """Emit a full dataset to out_dir/<config.tier>/. Returns the path to manifest.json.

    Layout produced:
      out_dir/<tier>/
        train.jsonl
        eval/<bucket_name>.jsonl       (one per config.eval_buckets entry)
        manifest.json                  (written last)
    """
```

Single public function. The CLI calls this; library callers call this. Returns the manifest path so callers can verify.

### 7.2 Internal structure

```python
def _row_seed(seed_base: int, split: str, bucket: str | None, index: int) -> int:
    key = f"{seed_base}|{split}|{bucket or ''}|{index}".encode()
    return int.from_bytes(hashlib.sha256(key).digest()[:8], "big")


_ID_RENDERERS: dict[str, Callable[[Program, ExecutionTrace], tuple[list[int], list[int]]]] = {
    "direct": tokeniser.render_direct,
    "cot":    tokeniser.render_cot,
}
_TEXT_RENDERERS: dict[str, Callable[[Program, ExecutionTrace], tuple[str, str]]] = {
    "direct": tokeniser.render_direct_text,
    "cot":    tokeniser.render_cot_text,
}


def _build_renders(program, trace, modes):
    out: dict[str, RenderedPrompt] = {}
    for m in modes:
        input_ids, target_ids = _ID_RENDERERS[m](program, trace)
        input_text, target_text = _TEXT_RENDERERS[m](program, trace)
        out[m] = RenderedPrompt(input_ids, target_ids, input_text, target_text)
    return out


def _emit_split(config, out_path, split, bucket, n_rows, seed_base):
    """Stream-write one .jsonl file. Returns (row_count, sha256_hexdigest)."""
    sha = hashlib.sha256()
    n = 0
    with out_path.open("w") as f:
        for i in range(n_rows):
            row_seed = _row_seed(seed_base, split, bucket.name if bucket else None, i)
            rng = random.Random(row_seed)
            if split == "train":
                axes = config.train_axes(rng)
            else:
                axes = dict(bucket.fixed_axes)
            program = config.build(rng, axes)
            trace = run(program)
            renders = _build_renders(program, trace, config.renders)
            meta = RowMeta(
                tier=config.tier, split=split,
                bucket=bucket.name if bucket else None,
                seed=row_seed, axes=axes, renders=config.renders,
            )
            row_dict = to_row(program, trace, meta, renders)
            line = json.dumps(row_dict, separators=(",", ":")) + "\n"
            sha.update(line.encode())
            f.write(line)
            n += 1
    return n, sha.hexdigest()


def emit(config, out_dir, seed_base=0):
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

    # Manifest written last — its presence means the emit completed.
    manifest_path = tier_dir / "manifest.json"
    manifest = {
        "tier": config.tier,
        "seed_base": seed_base,
        "tinyvm_version": _read_tinyvm_version(),
        "tinyvm_commit": _read_git_commit(),
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "files": files,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))
    return manifest_path
```

### 7.3 Failure semantics

- Crash mid-emit: partial files exist but no `manifest.json`. Re-running `emit` overwrites everything; idempotent (same seed_base → same files).
- Disk full / permission error: raises; caller decides retry strategy.
- Generator drift (a generator now produces a program `validate` rejects): Phase E generators self-validate per Task 31/34 fixes, so `gen_branched` / `gen_userop_trace` raise inside `_emit_split`. The half-written file is left behind without a manifest. The error propagates up.

## 8. Load (`load.py`)

```python
def load_jsonl(path: Path) -> Iterator[Row]:
    """Stream rows from a single .jsonl file as Row(program, trace, meta, renders) tuples."""
    with path.open() as f:
        for line in f:
            yield from_row(json.loads(line))


def load_split(dataset_dir: Path, split: str, bucket: str | None = None) -> Iterator[Row]:
    """Convenience: load all rows for a (split, bucket). Train: bucket=None."""
    if split == "train":
        return load_jsonl(dataset_dir / "train.jsonl")
    if bucket is None:
        raise ValueError("bucket required for split='eval'")
    return load_jsonl(dataset_dir / "eval" / f"{bucket}.jsonl")


def load_prompts(path: Path, mode: str = "direct") -> Iterator[tuple[list[int], list[int]]]:
    """Fast path: stream just (input_ids, target_ids) for the chosen render mode.

    Skips reconstruction of Program/ExecutionTrace; ideal for a PyTorch DataLoader
    where the IR isn't needed.
    """
    with path.open() as f:
        for line in f:
            row = json.loads(line)
            r = row["renders"][mode]
            yield r["input_ids"], r["target_ids"]


def load_manifest(dataset_dir: Path) -> dict:
    """Read manifest.json. Raise FileNotFoundError if missing — emit was incomplete."""
    return json.loads((dataset_dir / "manifest.json").read_text())
```

## 9. CLI (`__main__.py`)

Two subcommands. Argparse, no third-party deps.

```bash
# Emit a dataset:
python -m tinyvm.data emit --tier tier1 --out data/ --seed 0
python -m tinyvm.data emit --tier tier2 --out data/ --seed 42

# Verify an existing dataset:
python -m tinyvm.data verify --dataset data/tier1/
```

`verify` re-hashes every file listed in the manifest, compares against `manifest.files[f].sha256`, exits 0 on match, 2 on mismatch with a per-file diff. CI runs this before training to confirm the dataset hasn't drifted.

## 10. Testing strategy

| Layer | What it checks | How |
|---|---|---|
| **Schema round-trip** | `from_row(to_row(p, trace, meta, renders))` reconstructs all four pieces bit-exactly | Hypothesis-style: 200 programs across the three generators |
| **Config sanity** | Every `DatasetConfig` builds 10 programs without exception; each program passes `validate` | For each config in `CONFIGS`: 10 train + 10 per eval bucket |
| **Emit correctness** | Tiny dataset (train=50, eval=20/bucket) emits to `tmp_path`: expected files exist, row counts match, manifest hashes match file contents | `tmp_path` fixture |
| **Load round-trip** | `load_jsonl(emit(cfg, tmp))` yields programs identical to what the generator would produce given each row's `meta.seed` and `meta.axes` | tmp_path; sample 20 rows per tier |
| **Determinism** | Two `emit` calls with the same `seed_base` produce byte-identical files (SHA-256 every file) | tmp_path × 2 |
| **Integration trace-replay** | For every loaded row: `run(row.program).output == row.trace.output` (interpreter contract preserved through serialisation) | Sample 100 rows from a small emit |
| **Render fidelity** | For every loaded row and every populated render mode: re-rendering from the loaded Program reproduces the stored `input_ids` / `target_ids` exactly | Sample 50 rows per tier |
| **Verify CLI** | `python -m tinyvm.data verify --dataset <tmp>` returns 0 on a fresh emit; returns 2 after a row is corrupted | subprocess invocation in test |

All tests run in `pytest tinyvm/data/tests/` and complete in seconds (small dataset sizes).

## 11. Risks and mitigations

| Risk | Mitigation |
|---|---|
| **Dataset drift** — a future generator change produces silently different programs for the same seed_base | `verify` subcommand re-hashes against manifest; CI gate. Schema-round-trip test catches encode/decode regressions. |
| **Pre-rendered prompts go stale** — a future renderer fix changes output format; old datasets carry the old format | Manifest records `tinyvm_commit`; downstream loaders can refuse to consume datasets from a different commit, or a re-emit is cheap (~hours, not weeks). |
| **Tier 2 emit time too slow** — single-process 2–4 h | Documented in spec §3 decision 5; future `--workers N` flag is a bounded follow-up. Day 3 ships single-process. |
| **Disk usage too high at Tier 2** — ~5 GB | Documented in spec §7. `--no-text` flag (drop `*_text` fields) saves ~30%; `--render direct` saves another ~50% on Tier 2. Both are easy follow-ups. |
| **Manifest absent / corrupted** — emit crashed mid-run | `load_manifest` raises; users must re-emit. No silent corruption. |
| **JSON parsing overhead at train-time** — Tier 2 row at ~10 KB parses in ~1 ms per row; 500K rows ~8 min per epoch just for JSON | If this becomes a bottleneck during Day 4 training, the optimisation is to convert to a binary format (Parquet/Arrow) — orthogonal to this spec. |

## 12. Open questions deferred to implementation

- **Eval bucket axis values for Tier 2** are editorial calls (easy/medium/hard/ood_len_256). Reviewers may want different cells; trivial to edit `configs.TIER2.eval_buckets` without changing the pipeline code.
- **Render mode names** are strings (`"direct"`, `"cot"`). If we add userop renderers later, `"userop_direct"` and `"userop_with_decomposition"` follow the same pattern.
- **`tinyvm_version` source.** Either read from `pyproject.toml` at import time, or hard-code in `tinyvm.__version__`. Implementation should pick the lighter-weight approach.

## 13. References

- `Latent_State_as_Computer.docx` §11 (Datasets), §17 (Week 1 plan), §3.2 (difficulty axes table), §7.1 (Tier 2 training conditions).
- `docs/superpowers/specs/2026-05-15-tinyvm-module-design.md` — the upstream module spec, which deferred this pipeline as out of scope (§2).
- `docs/superpowers/plans/2026-05-15-tinyvm-module.md` — the 39-task plan that built the upstream module.
- PR #1 on `mr-siddy/FANC` — the upstream module implementation that this pipeline consumes.
