# FANC — Fast and Accurate Neural Computing

> A research mono-repo for the **"Latent State as Computer"** experimental program: studying how small language models internalise the structure of a register machine through synthetic curricula.

The first deliverable is **Tiny-VM**, a purpose-built toy ISA with a deterministic interpreter, a 64-token custom vocabulary, four program generators, and a data pipeline that materialises per-tier curricula to disk and to the HuggingFace Hub.

[![Tests](https://img.shields.io/badge/tests-185%20passing-brightgreen)](#testing)
[![Dataset](https://img.shields.io/badge/🤗-Genesis--AI--Labs%2Ftinyvm--tier1-yellow)](https://huggingface.co/datasets/Genesis-AI-Labs/tinyvm-tier1)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](#requirements)
[![License](https://img.shields.io/badge/license-MIT-green)](#license)

---

## Table of contents

- [Quick start](#quick-start)
- [What's in this repo](#whats-in-this-repo)
- [Live datasets](#live-datasets)
- [The Tiny-VM curriculum](#the-tiny-vm-curriculum)
- [Project structure](#project-structure)
- [Documentation](#documentation)
- [Code statistics](#code-statistics)
- [Testing](#testing)
- [Deferred work](#deferred-work)
- [Contributing](#contributing)
- [License](#license)

---

## Quick start

### Requirements

- Python 3.10+
- `huggingface_hub` and `datasets` (only for Hub upload — generation needs only stdlib + pytest)

### Install

```bash
git clone https://github.com/mr-siddy/FANC
cd FANC
pip install -e .
```

### Generate the Tier 1 dataset (340K rows, ~2 min)

```bash
python -m tinyvm.data emit --tier tier1 --out data/        # 200K train + 7×20K eval
python -m tinyvm.data verify --dataset data/tier1          # SHA-256 integrity check, exit 0
```

The result lands in `data/tier1/` (~1.8 GB) with `train.jsonl`, `eval/len_{8,16,32,48,64,96,128}.jsonl`, and `manifest.json`.

### Consume the dataset

**From the Hub (recommended for training):**

```python
from datasets import load_dataset

ds = load_dataset("Genesis-AI-Labs/tinyvm-tier1")
print(ds["train"][0]["renders"]["direct"]["input_text"])
```

**From local emit (preserves byte-integrity manifest):**

```python
from tinyvm.data import load_prompts

# Fast path — yields (input_ids, target_ids) tuples
for input_ids, target_ids in load_prompts("data/tier1/train.jsonl", mode="direct"):
    ...  # feed to your DataLoader
```

### Push your own emit to the Hub

```bash
huggingface-cli login                                      # first time only
python scripts/push_tier1_to_hub.py                        # three-layer push: raw + Parquet + README
```

---

## What's in this repo

| Component | Path | Description |
|---|---|---|
| **Tiny-VM core** | `tinyvm/` | ISA, interpreter, tokeniser, verifier, 4 generators |
| **Data pipeline** | `tinyvm/data/` | Per-tier JSONL emission, streaming readers, CLI, manifest |
| **Tests** | `tinyvm/tests/`, `tinyvm/data/tests/` | 185 passing tests across both modules |
| **Specs** | `docs/superpowers/specs/` | Design documents (one per major module) |
| **Plans** | `docs/superpowers/plans/` | Task-by-task implementation plans (39 + 18 tasks) |
| **Documentation** | `docs/` | This README + two detailed module docs (see below) |
| **Ops scripts** | `scripts/` | Hub upload, statistics, figure generation |
| **Figures** | `docs/figures/` | 5 measured-from-real-data PNG visualisations |

---

## Live datasets

| Dataset | Tier | Rows | Splits | Status |
|---|---|---:|---|---|
| [Genesis-AI-Labs/tinyvm-tier1](https://huggingface.co/datasets/Genesis-AI-Labs/tinyvm-tier1) | Tier 1 | 340,000 | `train` + 7 × `eval_len_<n>` | ✅ Public |
| `tinyvm-tier0` | Tier 0 | — | — | Not yet uploaded |
| `tinyvm-tier2` | Tier 2 | — | — | Not yet uploaded |

### Tier 1 highlights

- **200,000 train** programs at `n ∈ {8..32}` with `k ∈ {2, 4, 8}` active registers
- **140,000 eval** programs in 7 length-stratified buckets: `n ∈ {8, 16, 32, 48, 64, 96, 128}`
- **Length OOD** — train tops at `n=32`; `len_128` is **4× longer**, perfect for studying length generalisation
- **Two access paths on the Hub**: native `load_dataset` (Parquet) and raw JSONL (preserves SHA-256 manifest)
- **Bit-exact reproducibility** — every row reconstructable from `(meta.seed, meta.axes)` via `TIER1.build`

See [`docs/tinyvm_dataset.md`](docs/tinyvm_dataset.md) §9 for full statistical characterisation with figures.

---

## The Tiny-VM curriculum

A 6-tier sequence of synthetic datasets of increasing complexity:

| Tier | Status | Generator | Train | Eval | Render modes | Purpose |
|---|---|---|---:|---:|---|---|
| **0** | ✅ shipped | `gen_counter` | 100K | 10K | `direct` | Pipeline sanity / smoke |
| **1** | ✅ shipped + **live on Hub** | `gen_register_trace` | 200K | 140K | `direct` | Register file tracking, length generalisation |
| **2** | ✅ shipped | `gen_branched` | 500K | 40K | `direct` + `cot` | Branches, loops, optional stack; chain-of-thought |
| 3 | (reserved gap) | — | — | — | — | Reserved for an intermediate variant |
| 4 | ⏸ deferred | `gen_userop_trace` | — | — | `userop_*` | Few-shot userop induction (needs row-variant schema) |
| 5 | ⏸ future | — | — | — | `_text` | Qwen-class model hand-off |

All shipped tiers are emit-and-verify ready:

```bash
python -m tinyvm.data emit --tier tier0 --out data/    # ~30s
python -m tinyvm.data emit --tier tier1 --out data/    # ~2 min
python -m tinyvm.data emit --tier tier2 --out data/    # ~30-120 min (depending on hardware)
```

---

## Project structure

```
FANC/
├── README.md                            ← you are here
├── pyproject.toml                       Package metadata + pytest config
├── .gitignore                           data/, caches, build artefacts
│
├── tinyvm/                              The Tiny-VM module
│   ├── __init__.py
│   ├── isa.py                           Op enum, Instruction, Program
│   ├── interpreter.py                   run() → ExecutionTrace
│   ├── tokeniser.py                     64-vocab + encode/decode + 5 render modes
│   ├── generators.py                    gen_counter / gen_register_trace / gen_branched / gen_userop_trace
│   ├── verifier.py                      validate() + score_output() (RLVR reward)
│   ├── tests/                           135 tests
│   │
│   └── data/                            Data pipeline sub-package
│       ├── __init__.py                  Public re-exports
│       ├── schema.py                    Row, RowMeta, RenderedPrompt + to_row/from_row
│       ├── configs.py                   TIER0, TIER1, TIER2, CONFIGS dict
│       ├── emit.py                      emit() + manifest writer + SHA-256
│       ├── load.py                      load_jsonl / load_split / load_prompts / load_manifest
│       ├── __main__.py                  CLI: python -m tinyvm.data {emit,verify}
│       └── tests/                       50 tests
│
├── docs/                                Documentation
│   ├── tinyvm_documentation.md          Module reference (ISA, interpreter, generators, ...)
│   ├── tinyvm_dataset.md                Data pipeline + live Tier 1 dataset stats
│   ├── figures/                         5 PNG visualisations (regenerable)
│   ├── superpowers/
│   │   ├── specs/                       Design documents
│   │   └── plans/                       Implementation plans (task-by-task)
│
└── scripts/                             Ops tooling
    ├── push_tier1_to_hub.py             Three-layer HuggingFace push
    ├── tier1_readme.md                  Source for the Hub dataset card
    ├── compute_tier1_stats.py           Statistics over emitted data
    └── make_tier1_figures.py            Matplotlib figures for the docs
```

---

## Documentation

Two detailed module documents:

### [`docs/tinyvm_documentation.md`](docs/tinyvm_documentation.md) — Module reference

722 lines covering the Tiny-VM core: ISA (full opcode table), execution model (interpreter state machine), 64-token vocabulary, all 5 render modes, all 4 generators (with `gen_branched` flowchart), verifier's static checks, end-to-end worked example, complete public API surface, design decisions, extension points. Includes **4 Mermaid diagrams** (module dependency graph, interpreter state machine, render mode dispatch, branched generator flow).

### [`docs/tinyvm_dataset.md`](docs/tinyvm_dataset.md) — Pipeline + live dataset

831 lines covering the data pipeline: 6-tier curriculum, per-tier specs (TIER0/1/2), pipeline architecture (Mermaid diagram), row schema with annotated JSON example, determinism contract (the `_emit_split` reseed fix), manifest atomicity, CLI reference, **live Hub dataset documentation** including 5 PNG figures with real measurements over 160K analysed rows:

1. **Op frequency** — confirms the 9 fill ops at ~10.7% each (uniform-as-spec)
2. **Train program length distribution** — `n+2` uniform over `{10..34}`
3. **Per-bucket program length** — pin-tight at `n+2` per bucket
4. **Token sequence length per bucket** — box plots showing context-window requirements (256-token covers `len_48`; 1024 covers all)
5. **Register write distribution** — confirms per-program randomisation avoids positional bias

Plus a complete summary stats table, both access-path code examples, and a deferred-work TODO map with code locations.

### Design docs and plans

- `docs/superpowers/specs/2026-05-15-tinyvm-module-design.md` — Tiny-VM design spec
- `docs/superpowers/specs/2026-05-16-tinyvm-data-pipeline-design.md` — Data pipeline design spec
- `docs/superpowers/plans/2026-05-15-tinyvm-module.md` — 39-task plan that built the module
- `docs/superpowers/plans/2026-05-16-tinyvm-data-pipeline.md` — 18-task plan that built the pipeline

---

## Code statistics

| Module | Source LOC | Test LOC | Public functions / classes |
|---|---:|---:|---:|
| `tinyvm/` (core) | ~1,620 | ~2,400 | 19 functions, 8 classes / enums |
| `tinyvm/data/` (pipeline) | ~580 | ~600 | 10 functions, 3 classes |
| **Total** | **~2,200** | **~3,000** | 29 / 11 |

### Live Tier 1 dataset stats (measured)

| Quantity | Value |
|---|---:|
| Total rows generated | 340,000 |
| Total instructions across rows | 8,559,558 |
| Mean instructions per program | 25.2 |
| Median input tokens (train) | 104 |
| Max input tokens (any bucket) | 654 (in `len_128`) |
| Distinct opcodes used in Tier 1 | 11 |
| Emit wall time (single-process) | 2 minutes 12 seconds |
| Storage on disk | 1.8 GB JSONL |
| Storage on Hub (Parquet + raw) | ~2.5 GB |

---

## Testing

```bash
pytest tinyvm/ -v
```

| Test file | Tests | Coverage |
|---|---:|---|
| `tinyvm/tests/test_isa.py` | 8 | Op enum, Instruction, Program.build |
| `tinyvm/tests/test_interpreter.py` | 21 | run() semantics, clamping, div-by-zero, stack errors |
| `tinyvm/tests/test_tokeniser.py` | 34 | encode/decode round-trip, all 5 render modes, vocab size |
| `tinyvm/tests/test_verifier.py` | 17 | validate's 5 static checks |
| `tinyvm/tests/test_generators.py` | 34 | All 4 generators, ShapingSpec, GenSpec |
| `tinyvm/tests/test_export_*.py` | 8 | Golden-fixture export bundles |
| `tinyvm/tests/test_score_output.py` | (in verifier tests) | RLVR reward |
| `tinyvm/data/tests/test_schema.py` | 10 | to_row/from_row round-trip + property tests |
| `tinyvm/data/tests/test_configs.py` | 10 | Tier 0/1/2 config sanity |
| `tinyvm/data/tests/test_emit.py` | 22 | Streaming write, SHA-256, manifest, CLI subprocess |
| `tinyvm/data/tests/test_load.py` | 8 | All 4 load_* functions + error paths |
| `tinyvm/data/tests/test_pipeline.py` | 5 | End-to-end: trace replay, seed reproducibility, render fidelity, full-suite green |
| **Total** | **185** | All passing in **~1 s** |

---

## Deferred work

Tracked with TODO comments in the code; see [`docs/tinyvm_dataset.md`](docs/tinyvm_dataset.md) §14 for the full list. Highlights:

- **Tier 4 emission** (`UseropTrace` rows) — `gen_userop_trace` is implemented and tested but emits a row variant the current pipeline doesn't support yet
- **Multi-process emit** — single-process Tier 2 takes 30-120 min; a `--workers N` flag would parallelise per-row work
- **HuggingFace `Dataset.from_generator` adapter** — one-liner; defer until the train loop needs it
- **Storage optimisations** — `--no-text` and `--render direct` flags would shave 30-50% off Tier 2 disk

---

## Contributing

This is a research repository; please open an issue before sending a PR for non-trivial changes.

Development happens via the **subagent-driven-development** workflow documented in `docs/superpowers/` — every feature lands as: spec → plan → task-by-task implementation with two-stage review (spec compliance + code quality). The 185-test suite + integration tests in `test_pipeline.py` enforce the invariants.

Coding standards:

- Type hints on every public function
- `encoding="utf-8"` explicit on every file open
- Tests use `tmp_path` fixture for any I/O
- Commits follow conventional-commit format (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `ops:`)

---

## License

MIT. See individual files for details.

---

## Acknowledgements

- Parent research doc: `Latent_State_as_Computer.docx` (private)
- Methodology: Subagent-Driven Development via the `superpowers` plugin suite
- Hub hosting: HuggingFace + Genesis-AI-Labs
