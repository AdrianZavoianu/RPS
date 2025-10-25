#!/usr/bin/env python
"""Utility CLI for managing project catalogs and databases."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from services.project_service import (
    delete_project_context,
    list_project_summaries,
)


def cmd_list(args: argparse.Namespace) -> int:
    summaries = list_project_summaries()
    if not summaries:
        print("No projects found in catalog.")
        return 0

    for summary in summaries:
        ctx = summary.context
        print(
            f"- {ctx.name} (slug={ctx.slug}) | "
            f"Load cases: {summary.load_cases} "
            f"| Stories: {summary.stories} "
            f"| Result sets: {summary.result_sets} "
            f"| DB: {ctx.db_path}"
        )
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    if not args.name:
        print("Please specify --name for the project to delete.")
        return 1

    if not args.force:
        confirm = input(
            f"Delete project '{args.name}' from catalog and disk? [y/N]: "
        ).strip().lower()
        if confirm not in {"y", "yes"}:
            print("Aborted.")
            return 1

    if delete_project_context(args.name):
        print(f"Deleted project '{args.name}'.")
        return 0

    print(f"Project '{args.name}' not found.")
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Project catalog tooling.")
    subparsers = parser.add_subparsers(dest="command")

    list_parser = subparsers.add_parser("list", help="List catalogued projects.")
    list_parser.set_defaults(func=cmd_list)

    delete_parser = subparsers.add_parser("delete", help="Delete a project.")
    delete_parser.add_argument("--name", required=True, help="Project name to delete.")
    delete_parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt.",
    )
    delete_parser.set_defaults(func=cmd_delete)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
