#!/usr/bin/env python3
"""Static health check: every `module.attr` reference must actually exist.

Why
---
This repository was merged from two independent implementations of the same
library (IR-51-07).  The merge left a dozen scripts calling an API that the
surviving ``gems51`` package does not provide; they imported cleanly and failed
only at run time, so they looked healthy in CI.  IR-51-09.

What it checks
--------------
1. **API drift** — for every ``X.y`` attribute access where ``X`` is an imported
   ``gems51`` submodule, ``y`` must be defined in that submodule.  Local
   variables that shadow a module name are skipped, which is what makes the
   check usable rather than noisy.
2. **Import health** — every module in ``src/gems51`` must import.
3. **Tests** — ``tests/`` must collect.

Exit status is non-zero if any check fails, so it can gate CI.

    python3 scripts/check_repo_health.py [--json OUT]
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "src" / "gems51"
SCAN = [ROOT / "scripts", PKG]


def module_exports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    out: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    out.add(t.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            out.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names:
                out.add(a.asname or a.name.split(".")[0])
    return out


def collect_local_names(tree: ast.AST) -> set[str]:
    """Names bound anywhere in the file (so a local `stack` does not alias the module)."""
    bound: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign):
            for t in n.targets:
                for sub in ast.walk(t):
                    if isinstance(sub, ast.Name):
                        bound.add(sub.id)
        elif isinstance(n, (ast.For, ast.AsyncFor)):
            for sub in ast.walk(n.target):
                if isinstance(sub, ast.Name):
                    bound.add(sub.id)
        elif isinstance(n, ast.withitem) and n.optional_vars is not None:
            for sub in ast.walk(n.optional_vars):
                if isinstance(sub, ast.Name):
                    bound.add(sub.id)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            a = n.args
            for arg in (list(a.args) + list(a.posonlyargs) + list(a.kwonlyargs)
                        + ([a.vararg] if a.vararg else []) + ([a.kwarg] if a.kwarg else [])):
                bound.add(arg.arg)
    return bound


def module_aliases(tree: ast.AST) -> dict[str, str]:
    """alias -> gems51 submodule name, for `from gems51 import x as y` / `import gems51.x`."""
    out: dict[str, str] = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and (n.module or "").startswith("gems51"):
            base = (n.module or "").split(".")
            for a in n.names:
                if len(base) == 1:                   # from gems51 import strain as s
                    out[a.asname or a.name] = a.name
        elif isinstance(n, ast.Import):
            for a in n.names:
                if a.name.startswith("gems51."):
                    out[a.asname or a.name.split(".")[-1]] = a.name.split(".")[-1]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", dest="out", default=str(ROOT / "evidence" / "repo_health.json"))
    args = ap.parse_args()

    exports = {p.stem: module_exports(p) for p in sorted(PKG.glob("*.py"))}
    drift: list[dict] = []
    for base in SCAN:
        for p in sorted(base.rglob("*.py")):
            tree = ast.parse(p.read_text())
            aliases = module_aliases(tree)
            local = collect_local_names(tree)
            for n in ast.walk(tree):
                if not (isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)):
                    continue
                name = n.value.id
                if name in local or name not in aliases:
                    continue
                mod = aliases[name]
                if mod in exports and n.attr not in exports[mod] \
                        and not n.attr.startswith("__"):
                    drift.append(dict(file=str(p.relative_to(ROOT)), line=n.lineno,
                                      reference=f"{mod}.{n.attr}"))

    import_fail: list[dict] = []
    for p in sorted(PKG.glob("*.py")):
        if p.stem == "__init__":
            continue
        r = subprocess.run([sys.executable, "-c",
                            f"import sys; sys.path.insert(0, {str(ROOT / 'src')!r}); "
                            f"import gems51.{p.stem}"],
                           capture_output=True, text=True)
        if r.returncode != 0:
            import_fail.append(dict(module=f"gems51.{p.stem}",
                                    error=r.stderr.strip().splitlines()[-1][:200]))

    r = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q",
                        str(ROOT / "tests")],
                       capture_output=True, text=True,
                       env={**os.environ, "PYTHONPATH": str(ROOT / "src")})
    tests_ok = r.returncode == 0

    # ---- dead site links -------------------------------------------------
    # A hand-written docs page once pointed the big download button at a file
    # that no longer existed in docs/downloads/.  Every local href and src in
    # docs/*.html must resolve on disk.
    import re as _re
    dead = []
    docs = ROOT / "docs"
    for h in sorted(docs.glob("*.html")):
        text = h.read_text(errors="replace")
        for m in _re.finditer(r'(?:href|src)="([^"#]+)"', text):
            t = m.group(1)
            if t.startswith(("http://", "https://", "mailto:", "//", "data:")):
                continue
            if not (docs / t).exists():
                dead.append(dict(page=h.name, target=t))

    report = dict(api_drift=drift, import_failures=import_fail,
                  tests_collect_ok=tests_ok, dead_site_links=dead,
                  ok=(not drift and not import_fail and tests_ok and not dead))
    Path(args.out).write_text(json.dumps(report, indent=1) + "\n")
    for d in drift:
        print(f"API-DRIFT  {d['file']}:{d['line']}  {d['reference']}")
    for d in import_fail:
        print(f"IMPORT-FAIL {d['module']}: {d['error']}")
    for d in dead:
        print(f"DEAD-LINK  docs/{d['page']} -> {d['target']}")
    print(f"tests collect: {'ok' if tests_ok else 'FAILED'}")
    print(f"{'PASS' if report['ok'] else 'FAIL'} -> {args.out}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
