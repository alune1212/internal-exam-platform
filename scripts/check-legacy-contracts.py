#!/usr/bin/env python3
"""Fail when retired candidate identity contracts return to live source code."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SEARCH_ROOTS = (
    REPO_ROOT / "backend" / "app",
    REPO_ROOT / "frontend" / "src",
    REPO_ROOT / "docs",
    REPO_ROOT / "README.md",
)
ALLOWED_PATHS = {
    REPO_ROOT / "backend" / "app" / "ops" / "account_migration_preflight.py",
    REPO_ROOT / "backend" / "app" / "tests" / "test_account_migration_preflight.py",
    REPO_ROOT / "backend" / "app" / "tests" / "test_postgres_migration.py",
}
ALLOWED_PREFIXES = (
    REPO_ROOT / "backend" / "alembic" / "versions",
)
TEXT_SUFFIXES = {".md", ".py", ".ts", ".tsx", ".json", ".yml", ".yaml"}

# Build retired identifiers so this guard does not flag its own source.
RETIRED_IDENTIFIERS = (
    "employee" + "_no",
    "phone" + "_suffix",
    "should" + "_attend",
    "is_login" + "_sentinel",
)
RETIRED_STANDALONE_IMPORT_MARKERS = (
    "/api/admin/imports/templates/" + "candidates",
    "generate_" + "candidate_template",
    "import_" + "candidates_from_workbook",
)


def _is_allowed(path: Path) -> bool:
    if path in ALLOWED_PATHS:
        return True
    return any(path.is_relative_to(prefix) for prefix in ALLOWED_PREFIXES)


def _iter_source_files(root: Path):
    if root.is_file():
        yield root
        return
    for path in root.rglob("*"):
        if path.is_file() and path.suffix in TEXT_SUFFIXES:
            yield path


def main() -> int:
    findings: list[tuple[Path, int, str]] = []
    markers = RETIRED_IDENTIFIERS + RETIRED_STANDALONE_IMPORT_MARKERS
    for root in SEARCH_ROOTS:
        for path in _iter_source_files(root):
            if _is_allowed(path):
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                continue
            for line_number, line in enumerate(lines, start=1):
                if any(marker in line for marker in markers):
                    findings.append((path.relative_to(REPO_ROOT), line_number, line.strip()))

    if findings:
        print("Retired candidate identity contracts remain in live source:")
        for path, line_number, line in findings:
            print(f"{path}:{line_number}: {line}")
        print(
            "Only immutable Alembic history and the explicitly allowlisted account "
            "migration preflight fixtures may retain these identifiers."
        )
        return 1

    print("Legacy candidate identity contract check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
