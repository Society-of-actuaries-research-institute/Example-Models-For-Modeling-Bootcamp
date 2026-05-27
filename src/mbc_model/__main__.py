"""CLI entry point: ``python -m mbc_model [input_path]``."""

from __future__ import annotations

import sys
from pathlib import Path

from mbc_model.runner import run

_DEFAULT_INPUT = Path("inputs") / "Input 10 pol 25 scen table.xlsx"


def main() -> None:
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else _DEFAULT_INPUT
    if not input_path.exists():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)
    out = run(input_path)
    print(f"Results written to: {out}")


if __name__ == "__main__":
    main()
