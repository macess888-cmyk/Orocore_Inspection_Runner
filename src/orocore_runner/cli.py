from __future__ import annotations

import argparse
import sys

from pathlib import Path

from .runner import RunnerHold, inspect_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="orocore",
        description=(
            "Observer-only Orocore inspection runner."
        ),
    )

    commands = parser.add_subparsers(
        dest="command",
        required=True,
    )

    inspect_parser = commands.add_parser(
        "inspect",
        help="Inspect one transition package.",
    )

    inspect_parser.add_argument(
        "transition",
        type=Path,
        help="Path to transition JSON.",
    )

    inspect_parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path("inspection_output"),
        help="Output directory.",
    )

    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.command != "inspect":
        return 2

    try:
        artifacts = inspect_file(
            args.transition,
            args.out_dir,
        )
    except RunnerHold as exc:
        print(
            f"HOLD: {exc}",
            file=sys.stderr,
        )
        return 2

    print("OROCORE INSPECTION COMPLETE")
    print(f"RESULT:  {artifacts.result}")
    print(f"RECEIPT: {artifacts.receipt}")
    print(f"REPORT:  {artifacts.report}")
    print(
        f"RESULT SHA256: "
        f"{artifacts.result_sha256}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())