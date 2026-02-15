"""Lightweight layering audit for src package imports.

Scans Python files under src/ and reports package-to-package import edges.
Use --strict with --disallow to turn the report into a CI gate.
"""

from __future__ import annotations

import argparse
import ast
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Iterable

PACKAGE_ROOTS = ("gui", "services", "processing", "database", "config", "utils")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def _iter_imports(tree: ast.AST) -> Iterable[str]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name:
                    yield alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                yield node.module


def _find_package(path: Path, src_root: Path) -> str | None:
    try:
        rel = path.relative_to(src_root)
    except ValueError:
        return None
    if not rel.parts:
        return None
    top = rel.parts[0]
    return top if top in PACKAGE_ROOTS else None


def _parse_disallow(values: list[str]) -> set[tuple[str, str]]:
    disallowed: set[tuple[str, str]] = set()
    for value in values:
        if ":" not in value:
            raise ValueError(f"Invalid --disallow entry '{value}', expected src:dest")
        src, dest = value.split(":", 1)
        disallowed.add((src.strip(), dest.strip()))
    return disallowed


def main() -> int:
    parser = argparse.ArgumentParser(description="Report package import edges under src/")
    parser.add_argument("--show-files", action="store_true", help="Show example files per edge")
    parser.add_argument("--max-files", type=int, default=5, help="Max files per edge to show")
    parser.add_argument(
        "--disallow",
        action="append",
        default=[],
        help="Disallow edge in the form src:dest (repeatable)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if disallowed edges or cycles are found",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    src_root = root / "src"
    if not src_root.exists():
        raise SystemExit("src/ directory not found")

    edges: DefaultDict[tuple[str, str], list[str]] = defaultdict(list)
    parse_errors: list[str] = []

    for path in src_root.rglob("*.py"):
        pkg = _find_package(path, src_root)
        if not pkg:
            continue
        try:
            tree = ast.parse(_read_text(path))
        except SyntaxError as exc:
            parse_errors.append(f"{path}: {exc}")
            continue

        for module in _iter_imports(tree):
            top = module.split(".", 1)[0]
            if top in PACKAGE_ROOTS and top != pkg:
                edges[(pkg, top)].append(str(path.relative_to(root)))

    disallowed = _parse_disallow(args.disallow)

    print("Layering audit")
    print(f"Packages: {', '.join(PACKAGE_ROOTS)}")
    print("Edges:")
    for (src, dest), files in sorted(edges.items()):
        print(f"  {src} -> {dest} ({len(files)})")
        if args.show_files:
            for file_path in files[: args.max_files]:
                print(f"    - {file_path}")
            if len(files) > args.max_files:
                print(f"    ... {len(files) - args.max_files} more")

    if parse_errors:
        print("Parse errors:")
        for err in parse_errors:
            print(f"  - {err}")

    cycles: list[tuple[str, str]] = []
    for src, dest in edges:
        if (dest, src) in edges and (dest, src) not in cycles:
            cycles.append((src, dest))

    if cycles:
        print("Potential cycles:")
        for src, dest in sorted(cycles):
            print(f"  {src} <-> {dest}")

    violations: list[str] = []
    for src, dest in sorted(edges):
        if (src, dest) in disallowed:
            violations.append(f"{src} -> {dest}")

    if violations:
        print("Disallowed edges:")
        for entry in violations:
            print(f"  {entry}")

    if args.strict and (violations or cycles):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
