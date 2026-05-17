"""Push the emitted Tier 1 dataset to Genesis-AI-Labs/tinyvm-tier1.

Three layers:
  1. Raw JSONL + manifest under raw/ — preserves byte/SHA integrity.
     Consumers can re-hydrate with `tinyvm.data.load_jsonl` and verify
     with `python -m tinyvm.data verify --dataset <local>`.
  2. HF DatasetDict at root — `datasets.load_dataset(...)` works directly.
     Uses an explicit Features schema (not inference) so:
       - `meta.bucket` is `string` (nullable) across train and eval splits,
         not `null` for train + `string` for eval (which would fail merge).
       - `meta.seed` is `uint64`, not `float64` — preserves the full 64-bit
         SHA-derived seed (float64 only has 53 bits of mantissa).
  3. README.md (dataset card) — describes both access paths.

Run after `python -m tinyvm.data emit --tier tier1 --out data/`.
"""
from __future__ import annotations

import sys
from pathlib import Path

from datasets import Dataset, DatasetDict, Features, Sequence, Value
from huggingface_hub import HfApi

REPO_ID = "Genesis-AI-Labs/tinyvm-tier1"
LOCAL_ROOT = Path("data/tier1")
README_PATH = Path("scripts/tier1_readme.md")

# --- Explicit schema -------------------------------------------------------

INSTRUCTION_FEAT = {
    "op": Value("string"),
    "args": Sequence(Value("int64")),
    "label": Value("string"),
    "target": Value("string"),
}
TRACE_STEP_FEAT = {
    "pc": Value("int64"),
    "regs": Sequence(Value("int64")),
    "stack": Sequence(Value("int64")),
    "emitted": Value("int64"),
}
FEATURES = Features({
    "meta": {
        "tier": Value("string"),
        "split": Value("string"),
        "bucket": Value("string"),       # nullable; None for train, "len_X" for eval
        "seed": Value("uint64"),          # full 64-bit; float64 would lose precision
        "axes": {"n": Value("int64"), "k": Value("int64")},
        "renders": Sequence(Value("string")),
    },
    "program": [INSTRUCTION_FEAT],
    "trace": {
        "steps": [TRACE_STEP_FEAT],
        "output": Sequence(Value("int64")),
        "halted": Value("bool"),
    },
    "renders": {
        "direct": {
            "input_ids": Sequence(Value("int64")),
            "target_ids": Sequence(Value("int64")),
            "input_text": Value("string"),
            "target_text": Value("string"),
        },
    },
})


def upload_raw(api: HfApi) -> None:
    print(f"[raw] Uploading {LOCAL_ROOT} → {REPO_ID}/raw/ ...")
    api.upload_folder(
        folder_path=str(LOCAL_ROOT),
        path_in_repo="raw",
        repo_id=REPO_ID,
        repo_type="dataset",
        commit_message="raw: tier1 train.jsonl + eval/* + manifest.json (seed_base=0)",
    )
    print(f"[raw] Done.")


def build_dataset_dict() -> DatasetDict:
    splits: dict[str, Dataset] = {}
    train_path = LOCAL_ROOT / "train.jsonl"
    print(f"[dd]  Loading train split from {train_path} ...")
    splits["train"] = Dataset.from_json(str(train_path), features=FEATURES)
    print(f"[dd]  train: {len(splits['train'])} rows")
    for bucket_path in sorted((LOCAL_ROOT / "eval").glob("*.jsonl")):
        split_name = f"eval_{bucket_path.stem}"
        print(f"[dd]  Loading {split_name} from {bucket_path.name} ...")
        splits[split_name] = Dataset.from_json(str(bucket_path), features=FEATURES)
        print(f"[dd]  {split_name}: {len(splits[split_name])} rows")
    return DatasetDict(splits)


def push_dataset_dict(dd: DatasetDict) -> None:
    print(f"[dd]  Pushing DatasetDict to {REPO_ID} ...")
    dd.push_to_hub(
        repo_id=REPO_ID,
        commit_message="dataset: tier1 splits (train + 7 eval buckets, seed_base=0; uint64 seed)",
    )
    print(f"[dd]  Done.")


def upload_readme(api: HfApi) -> None:
    if not README_PATH.exists():
        print(f"[readme] {README_PATH} missing; skipping.", file=sys.stderr)
        return
    print(f"[readme] Uploading {README_PATH} → {REPO_ID}/README.md ...")
    api.upload_file(
        path_or_fileobj=str(README_PATH),
        path_in_repo="README.md",
        repo_id=REPO_ID,
        repo_type="dataset",
        commit_message="docs: dataset card with native + raw access paths",
    )
    print(f"[readme] Done.")


def main() -> int:
    if not LOCAL_ROOT.exists():
        print(f"ERROR: {LOCAL_ROOT} does not exist. Run `python -m tinyvm.data emit --tier tier1 --out data/` first.", file=sys.stderr)
        return 1
    if not (LOCAL_ROOT / "manifest.json").exists():
        print(f"ERROR: {LOCAL_ROOT}/manifest.json missing — emit may have crashed. Re-emit.", file=sys.stderr)
        return 1

    api = HfApi()
    upload_raw(api)
    push_dataset_dict(build_dataset_dict())
    upload_readme(api)

    print(f"\n✓ Three layers pushed to https://huggingface.co/datasets/{REPO_ID}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
