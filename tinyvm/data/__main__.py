"""CLI: python -m tinyvm.data emit/verify ..."""
from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from tinyvm.data.configs import CONFIGS
from tinyvm.data.emit import emit
from tinyvm.data.load import load_manifest


def _cmd_emit(args: argparse.Namespace) -> int:
    if args.tier not in CONFIGS:
        print(f"unknown tier: {args.tier} (known: {sorted(CONFIGS)})", file=sys.stderr)
        return 2
    config = CONFIGS[args.tier]
    out_dir = Path(args.out)
    manifest_path = emit(config, out_dir, seed_base=args.seed)
    print(f"manifest: {manifest_path}")
    return 0


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


if __name__ == "__main__":
    sys.exit(main())
