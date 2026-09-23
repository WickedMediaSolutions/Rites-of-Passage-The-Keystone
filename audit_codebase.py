#!/usr/bin/env python3
"""
ROP Codebase Audit
------------------
Read-only Python codebase audit intended to be run locally from the project root.

Checks:
- Python syntax via ast.parse
- Python bytecode compilation via py_compile
- unresolved local-module imports (best-effort static check)
- Git merge-conflict markers
- null bytes / unreadable source files
- duplicate top-level class/function definitions
- Ruff, if already installed
- Pyright, if already installed
- pytest collection, if pytest is already installed

It DOES NOT:
- modify project files
- install packages
- run the full test suite
- import your game modules directly
- start Evennia
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import os
import py_compile
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


EXCLUDED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    "node_modules",
    "venv",
    ".venv",
    "env",
    ".env",
    "dist",
    "build",
    "site-packages",
}

CONFLICT_MARKERS = ("<<<<<<<", "=======", ">>>>>>>")

@dataclass
class Finding:
    severity: str
    path: str
    line: int | None
    message: str

    def render(self) -> str:
        loc = self.path
        if self.line is not None:
            loc += f":{self.line}"
        return f"[{self.severity}] {loc} - {self.message}"


def iter_python_files(root: Path) -> Iterable[Path]:
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        current_path = Path(current)
        for name in files:
            if name.endswith(".py"):
                yield current_path / name


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def check_source(path: Path, root: Path, findings: list[Finding]) -> ast.AST | None:
    rpath = rel(path, root)

    try:
        raw = path.read_bytes()
    except OSError as exc:
        findings.append(Finding("ERROR", rpath, None, f"Cannot read file: {exc}"))
        return None

    if b"\x00" in raw:
        findings.append(Finding("ERROR", rpath, None, "Null byte found in Python source"))
        return None

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        findings.append(Finding("ERROR", rpath, None, f"Not valid UTF-8: {exc}"))
        return None

    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.lstrip()
        if any(stripped.startswith(marker) for marker in CONFLICT_MARKERS):
            findings.append(
                Finding("ERROR", rpath, lineno, "Possible unresolved Git merge-conflict marker")
            )

    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        findings.append(
            Finding(
                "ERROR",
                rpath,
                exc.lineno,
                f"SyntaxError: {exc.msg}"
            )
        )
        return None

    return tree


def check_compile(path: Path, root: Path, findings: list[Finding]) -> None:
    rpath = rel(path, root)
    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError as exc:
        findings.append(Finding("ERROR", rpath, None, f"Compile failure: {exc.msg}"))
    except Exception as exc:
        findings.append(Finding("ERROR", rpath, None, f"Unexpected compile failure: {exc}"))


def check_duplicate_top_level_defs(
    tree: ast.AST, path: Path, root: Path, findings: list[Finding]
) -> None:
    rpath = rel(path, root)
    seen: dict[str, int] = {}

    body = getattr(tree, "body", [])
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            name = node.name
            if name in seen:
                findings.append(
                    Finding(
                        "WARN",
                        rpath,
                        getattr(node, "lineno", None),
                        f"Duplicate top-level definition '{name}' "
                        f"(first defined at line {seen[name]})"
                    )
                )
            else:
                seen[name] = getattr(node, "lineno", 0)


def build_local_module_index(root: Path, pyfiles: list[Path]) -> set[str]:
    modules: set[str] = set()

    for path in pyfiles:
        try:
            rp = path.relative_to(root)
        except ValueError:
            continue

        parts = list(rp.parts)
        if not parts or parts[-1].startswith("."):
            continue

        filename = parts[-1]
        if filename == "__init__.py":
            modparts = parts[:-1]
        else:
            modparts = parts[:-1] + [path.stem]

        if modparts:
            modules.add(".".join(modparts))

    return modules


def top_level_local_names(local_modules: set[str]) -> set[str]:
    return {m.split(".", 1)[0] for m in local_modules if m}


def check_imports(
    tree: ast.AST,
    path: Path,
    root: Path,
    local_top_levels: set[str],
    findings: list[Finding],
) -> None:
    """
    Best-effort only.

    We deliberately avoid importing project modules because imports may initialize
    Django/Evennia or have other side effects. Standard-library and installed
    third-party modules are checked with find_spec where safe.
    """
    rpath = rel(path, root)

    for node in ast.walk(tree):
        names: list[tuple[str, int | None]] = []

        if isinstance(node, ast.Import):
            names.extend((alias.name, getattr(node, "lineno", None)) for alias in node.names)

        elif isinstance(node, ast.ImportFrom):
            if node.level:
                # Relative imports are skipped; resolving them statically is noisy.
                continue
            if node.module:
                names.append((node.module, getattr(node, "lineno", None)))

        for module_name, lineno in names:
            top = module_name.split(".", 1)[0]

            if top in local_top_levels:
                continue

            try:
                spec = importlib.util.find_spec(top)
            except Exception:
                # Some packages behave badly during spec lookup. Avoid false positives.
                continue

            if spec is None:
                findings.append(
                    Finding(
                        "WARN",
                        rpath,
                        lineno,
                        f"Import may be unresolved in this environment: '{module_name}'"
                    )
                )


def run_tool(
    name: str,
    cmd: list[str],
    root: Path,
    report_lines: list[str],
    timeout: int = 300,
) -> int | None:
    exe = shutil.which(cmd[0])
    if exe is None:
        report_lines.append(f"\n## {name}\nSKIPPED: {cmd[0]} is not installed or not on PATH.\n")
        return None

    report_lines.append(f"\n## {name}\nCommand: {' '.join(cmd)}\n")

    try:
        proc = subprocess.run(
            cmd,
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            errors="replace",
        )
        output = proc.stdout.strip()
        report_lines.append(output if output else "(no output)")
        report_lines.append(f"\nExit code: {proc.returncode}\n")
        return proc.returncode

    except subprocess.TimeoutExpired as exc:
        output = ""
        if exc.stdout:
            output = exc.stdout if isinstance(exc.stdout, str) else exc.stdout.decode(errors="replace")
        report_lines.append(output.strip())
        report_lines.append(f"\nTIMEOUT after {timeout} seconds.\n")
        return 124

    except OSError as exc:
        report_lines.append(f"FAILED TO RUN: {exc}\n")
        return 125


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Python codebase audit.")
    parser.add_argument(
        "root",
        nargs="?",
        default=".",
        help="Project root to scan (default: current directory)",
    )
    parser.add_argument(
        "--no-import-check",
        action="store_true",
        help="Skip best-effort installed/local import checks.",
    )
    parser.add_argument(
        "--no-tools",
        action="store_true",
        help="Skip Ruff, Pyright, and pytest collection.",
    )
    parser.add_argument(
        "--report",
        default="code_audit_report.txt",
        help="Output report filename (default: code_audit_report.txt)",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    report_path = root / args.report

    if not root.is_dir():
        print(f"ERROR: Not a directory: {root}")
        return 2

    print(f"Scanning: {root}")
    print("Read-only audit; project source files will not be modified.")

    pyfiles = sorted(iter_python_files(root))
    findings: list[Finding] = []
    parsed: dict[Path, ast.AST] = {}

    local_modules = build_local_module_index(root, pyfiles)
    local_top_levels = top_level_local_names(local_modules)

    for index, path in enumerate(pyfiles, start=1):
        if index % 100 == 0:
            print(f"  Checked {index}/{len(pyfiles)} files...")

        tree = check_source(path, root, findings)
        check_compile(path, root, findings)

        if tree is not None:
            parsed[path] = tree
            check_duplicate_top_level_defs(tree, path, root, findings)
            if not args.no_import_check:
                check_imports(tree, path, root, local_top_levels, findings)

    errors = [f for f in findings if f.severity == "ERROR"]
    warnings = [f for f in findings if f.severity == "WARN"]

    report: list[str] = [
        "ROP CODEBASE AUDIT REPORT",
        "=" * 80,
        f"Root: {root}",
        f"Python files scanned: {len(pyfiles)}",
        f"Static errors: {len(errors)}",
        f"Static warnings: {len(warnings)}",
        "",
        "## STATIC FINDINGS",
    ]

    if findings:
        report.extend(f.render() for f in findings)
    else:
        report.append("No static findings.")

    tool_failures = 0

    if not args.no_tools:
        # Ruff is intentionally run only if already installed.
        code = run_tool(
            "RUFF",
            ["ruff", "check", ".", "--output-format", "concise"],
            root,
            report,
        )
        if code not in (None, 0):
            tool_failures += 1

        # Pyright is intentionally run only if already installed.
        code = run_tool(
            "PYRIGHT",
            ["pyright"],
            root,
            report,
        )
        if code not in (None, 0):
            tool_failures += 1

        # Collection catches broken test imports without running the test suite.
        pytest_cmd = [sys.executable, "-m", "pytest", "--collect-only", "-q"]
        try:
            import pytest  # noqa: F401
            report.append("\n## PYTEST COLLECTION\nCommand: " + " ".join(pytest_cmd) + "\n")
            proc = subprocess.run(
                pytest_cmd,
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=300,
                errors="replace",
            )
            report.append(proc.stdout.strip() or "(no output)")
            report.append(f"\nExit code: {proc.returncode}\n")
            if proc.returncode != 0:
                tool_failures += 1
        except ImportError:
            report.append("\n## PYTEST COLLECTION\nSKIPPED: pytest is not installed.\n")
        except subprocess.TimeoutExpired as exc:
            if exc.stdout:
                output = exc.stdout if isinstance(exc.stdout, str) else exc.stdout.decode(errors="replace")
                report.append(output.strip())
            report.append("\nTIMEOUT after 300 seconds.\n")
            tool_failures += 1

    report.extend(
        [
            "",
            "## SUMMARY",
            f"Python files scanned: {len(pyfiles)}",
            f"Static errors: {len(errors)}",
            f"Static warnings: {len(warnings)}",
            f"Optional tool checks with non-zero exit: {tool_failures}",
            "",
            "NOTE:",
            "- WARN import findings are best-effort and can be false positives in framework-managed environments.",
            "- A clean static audit does not replace runtime/gameplay tests.",
            "- pytest was collection-only; the full test suite was NOT run.",
        ]
    )

    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")

    print()
    print("=" * 72)
    print(f"Python files scanned : {len(pyfiles)}")
    print(f"Static errors        : {len(errors)}")
    print(f"Static warnings      : {len(warnings)}")
    print(f"Tool check failures  : {tool_failures}")
    print(f"Report written to    : {report_path}")
    print("=" * 72)

    if errors or tool_failures:
        print("AUDIT RESULT: ISSUES FOUND")
        return 1

    print("AUDIT RESULT: NO HARD STATIC ERRORS FOUND")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
