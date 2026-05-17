---
license: mit
task_categories:
  - text-generation
  - other
language:
  - en
tags:
  - synthetic
  - reasoning
  - program-execution
  - tiny-vm
  - interpretability
pretty_name: Tiny-VM Tier 1 (Register Traces)
size_categories:
  - 100K<n<1M
configs:
  - config_name: default
    data_files:
      - split: train
        path: data/train-*
      - split: eval_len_8
        path: data/eval_len_8-*
      - split: eval_len_16
        path: data/eval_len_16-*
      - split: eval_len_32
        path: data/eval_len_32-*
      - split: eval_len_48
        path: data/eval_len_48-*
      - split: eval_len_64
        path: data/eval_len_64-*
      - split: eval_len_96
        path: data/eval_len_96-*
      - split: eval_len_128
        path: data/eval_len_128-*
---

# Tiny-VM Tier 1 — Register Traces

Synthetic dataset of straight-line Tiny-VM programs with full execution traces and pre-rendered training prompts. Tier 1 of the **FANC "Latent State as Computer"** experimental curriculum, focused on **register-file tracking under bounded program length**.

- **200,000** train programs
- **140,000** stratified eval programs (7 buckets × 20,000, one per program length `n ∈ {8, 16, 32, 48, 64, 96, 128}`)
- Generator: `tinyvm.generators.gen_register_trace` (LOAD / ADD / SUB / MOV / PRINT, no control flow)
- Per-row: full `Program` (instruction list) + `ExecutionTrace` (per-step register snapshots, output stream, halted flag) + `direct`-mode pre-rendered prompt (token IDs and surface text)
- Deterministic: every row is reconstructable from `(meta.seed, meta.axes)` via `tinyvm.data.configs.TIER1.build`
- Byte-integrity: every file's SHA-256 is in `manifest.json` (raw layout); `python -m tinyvm.data verify` re-hashes against it
- Seed base: `0`

## Two access paths

### 1. Native HF datasets (Parquet)

```python
from datasets import load_dataset

ds = load_dataset("Genesis-AI-Labs/tinyvm-tier1")
ds["train"]          # 200,000 rows
ds["eval_len_16"]    # 20,000 rows (one per length bucket)

# Each row has: meta, program, trace, renders
row = ds["train"][0]
print(row["meta"]["seed"], row["meta"]["axes"])
print(row["renders"]["direct"]["input_text"])    # surface tokens
print(row["renders"]["direct"]["input_ids"])     # 64-vocab token IDs
```

### 2. Raw JSONL + manifest (byte-integrity)

The exact files emitted by `python -m tinyvm.data emit --tier tier1 --out data/` are mirrored under `raw/` on the Hub. Download and verify:

```bash
huggingface-cli download Genesis-AI-Labs/tinyvm-tier1 \
    --repo-type dataset \
    --include "raw/*" \
    --local-dir ./data

python -m tinyvm.data verify --dataset ./data/raw    # exits 0 if SHA-256 matches manifest
```

Then stream with the project's loader (skip Program/Trace reconstruction for fast DataLoader pipelines):

```python
from tinyvm.data import load_jsonl, load_prompts

# Full row with reconstructed Program + ExecutionTrace.
for row in load_jsonl("data/raw/train.jsonl"):
    ...

# Fast path: just (input_ids, target_ids) tuples for the chosen render mode.
for input_ids, target_ids in load_prompts("data/raw/train.jsonl", mode="direct"):
    ...
```

## Schema

Each row is a JSON object with four top-level keys:

| Key | Type | Description |
|---|---|---|
| `meta` | object | `{tier: "tier1", split: "train"\|"eval", bucket: <name>\|null, seed: int, axes: {n: int, k: int}, renders: ["direct"]}` |
| `program` | array | List of instruction dicts: `{op: "LOAD"\|"ADD"\|..., args: [...], label?: str, target?: str}` |
| `trace` | object | `{steps: [{pc: int, regs: [int×8]}, ...], output: [int, ...], halted: bool}` |
| `renders` | object | `{direct: {input_ids: [int], target_ids: [int], input_text: str, target_text: str}}` |

The vocabulary is the project's custom 64-token vocabulary (see `tinyvm.tokeniser`). Token 0 is `<pad>`, registers are `R0..R7`, etc.

## Tier 1 axes

| Axis | Range / Values | Meaning |
|---|---|---|
| `n` | uniformly sampled from `[8, 32]` (train); fixed per eval bucket | Program length in instructions |
| `k` | uniformly chosen from `{2, 4, 8}` | Number of distinct registers used |

Eval buckets are length-stratified at `n ∈ {8, 16, 32, 48, 64, 96, 128}` with `k=4` fixed. The `len_48` through `len_128` buckets test **length generalisation** beyond the training distribution (which tops out at `n=32`) — the `len_128` bucket is 4× the longest training program.

## Reproducibility

The dataset is bit-exact reproducible:

```bash
git clone https://github.com/mr-siddy/FANC
cd FANC
pip install -e .
python -m tinyvm.data emit --tier tier1 --out data/ --seed 0
python -m tinyvm.data verify --dataset data/tier1   # exit 0
```

The verify step re-hashes every emitted file's SHA-256 and compares against `manifest.json`. Manifest also records `tinyvm_commit` (git SHA at emit time) so consumers can pin to the exact code that produced the data.

## Provenance

- **Project:** FANC — "Latent State as Computer" (research)
- **Code:** [github.com/mr-siddy/FANC](https://github.com/mr-siddy/FANC) — `tinyvm/data/` sub-package
- **Spec:** `docs/superpowers/specs/2026-05-16-tinyvm-data-pipeline-design.md`
- **Parent doc:** `Latent_State_as_Computer.docx` §11.2 (dataset sizes), §17 (Day 3)
- **Companion datasets** (to come): `tinyvm-tier0` (counter programs), `tinyvm-tier2` (branched programs with CoT renders)

## License

MIT. Use freely.
