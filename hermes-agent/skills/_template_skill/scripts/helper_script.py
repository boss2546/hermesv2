#!/usr/bin/env python3
"""Helper script for template skill.

Demonstrates cross-platform execution (stdlib only, pathlib, argparse, json).
"""

import argparse
import json
import sys
from pathlib import Path


def process_data(input_path: Path, output_path: Path | None = None) -> dict:
    """Read input data, transform it, and optionally write output."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    try:
        content = input_path.read_text(encoding="utf-8")
        data = json.loads(content) if input_path.suffix == ".json" else {"raw": content}
    except Exception as exc:
        raise ValueError(f"Failed to read/parse input: {exc}") from exc

    # Perform deterministic business logic / transformation
    result = {
        "status": "success",
        "processed_items": len(data) if isinstance(data, (list, dict)) else 1,
        "payload": data,
    }

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    return result


def main():
    parser = argparse.ArgumentParser(description="Deterministic helper for template skill.")
    parser.add_argument("--input", "-i", type=Path, required=True, help="Path to input file")
    parser.add_argument("--output", "-o", type=Path, default=None, help="Path to write output")
    args = parser.parse_args()

    try:
        res = process_data(args.input, args.output)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        sys.exit(0)
    except Exception as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
