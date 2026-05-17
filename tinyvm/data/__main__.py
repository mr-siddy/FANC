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
