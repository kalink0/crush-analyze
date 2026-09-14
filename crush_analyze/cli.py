from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, runner
from .modules import UnknownModuleError, get_module, list_modules


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="crush-analyze")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list-modules", help="List bundled analyzer modules as JSON")

    run_parser = subparsers.add_parser("run", help="Run an analyzer module against an input directory")
    source = run_parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--module", help="ID of a bundled module")
    source.add_argument(
        "--module-path",
        help="Path to an external, non-vendored module file (dev mode, requires --dev)",
    )
    run_parser.add_argument("--input", required=True, help="Input directory to analyze")
    run_parser.add_argument("--output", required=True, help="Output JSON file path (contract v1)")
    run_parser.add_argument(
        "--dev",
        action="store_true",
        help="Mark this run as dev mode; required together with --module-path",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "list-modules":
        print(json.dumps(list_modules(), indent=2))
        return 0

    if bool(args.module_path) != bool(args.dev):
        parser.error("--module-path and --dev must be used together")

    input_path = Path(args.input)
    if not input_path.is_dir():
        print(f"error: --input {input_path} is not a directory", file=sys.stderr)
        return 2

    try:
        if args.module_path:
            module_info = runner.load_external_module(Path(args.module_path))
            module_source = f"external:{args.module_path}"
        else:
            module_info = get_module(args.module)
            module_source = "bundled"
    except (UnknownModuleError, runner.ModuleLoadError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    output_path = Path(args.output)
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"error: cannot create output directory: {exc}", file=sys.stderr)
        return 2

    result = runner.run(module_info, input_path, dev_mode=args.dev, module_source=module_source)

    try:
        output_path.write_text(json.dumps(result, indent=2))
    except OSError as exc:
        print(f"error: cannot write output file: {exc}", file=sys.stderr)
        return 2

    return 1 if result["status"] == "error" else 0


if __name__ == "__main__":
    sys.exit(main())
