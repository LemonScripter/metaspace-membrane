#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace.Bio Engine Project — CapabilityAnalyzer (code -> constitution synthesis)

Statically detects the REAL effects of code (filesystem, network, env, subprocess,
hardware bus, import path) plus value comparisons (invariants), and synthesises a
draft `constitution.bio` from them (CAPABILITIES {} + INVARIANTS {} block).

This is the static, build-time part of the "code -> constitution" path.
HONEST LIMIT: this is a STATIC, name-based heuristic. The deterministic guarantee is
provided by the runtime membrane; this is the synthesis + the basis of the CI gate.

Usage:
    python capability_analyzer.py <path_to_python_file>
"""

import ast
import sys
import os
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Effect signatures: dotted-name (or bare function name) -> (kind, mode)
# ---------------------------------------------------------------------------
CALL_SIGNATURES = {
    # subprocess
    "os.system": ("SUBPROCESS", "exec"),
    "os.popen": ("SUBPROCESS", "exec"),
    "subprocess.run": ("SUBPROCESS", "exec"),
    "subprocess.call": ("SUBPROCESS", "exec"),
    "subprocess.Popen": ("SUBPROCESS", "exec"),
    "subprocess.check_output": ("SUBPROCESS", "exec"),
    # network - outbound
    "requests.get": ("NETWORK", "out"),
    "requests.post": ("NETWORK", "out"),
    "requests.put": ("NETWORK", "out"),
    "requests.delete": ("NETWORK", "out"),
    "requests.request": ("NETWORK", "out"),
    "httpx.get": ("NETWORK", "out"),
    "httpx.post": ("NETWORK", "out"),
    "urllib.request.urlopen": ("NETWORK", "out"),
    "socket.socket": ("NETWORK", "out"),
    # network - listen
    "uvicorn.run": ("NETWORK", "listen"),
    # env
    "os.getenv": ("ENV", "read"),
    "os.environ.get": ("ENV", "read"),
    # filesystem - write
    "os.remove": ("FILESYSTEM", "write"),
    "os.unlink": ("FILESYSTEM", "write"),
    "os.mkdir": ("FILESYSTEM", "write"),
    "os.makedirs": ("FILESYSTEM", "write"),
    "shutil.rmtree": ("FILESYSTEM", "write"),
    "shutil.copy": ("FILESYSTEM", "write"),
    "shutil.move": ("FILESYSTEM", "write"),
    # filesystem - read (framework + pathlib)
    "FileResponse": ("FILESYSTEM", "read"),
    "StaticFiles": ("FILESYSTEM", "read"),
    # hardware bus (dotted + bare fallback below)
    "smbus.SMBus": ("HARDWARE", "i2c"),
    "smbus2.SMBus": ("HARDWARE", "i2c"),
    "spidev.SpiDev": ("HARDWARE", "spi"),
    "serial.Serial": ("HARDWARE", "uart"),
}

# Bare-name fallback (alias-independent recognition, e.g. `import smbus2 as smbus`)
BARE_SIGNATURES = {
    "SMBus": ("HARDWARE", "i2c"),
    "SpiDev": ("HARDWARE", "spi"),
    "Serial": ("HARDWARE", "uart"),
    "FileResponse": ("FILESYSTEM", "read"),
    "StaticFiles": ("FILESYSTEM", "read"),
}

# Method-name based detection (the receiver type is often statically unknown)
METHOD_SIGNATURES = {
    "read_text": ("FILESYSTEM", "read"),
    "read_bytes": ("FILESYSTEM", "read"),
    "write_text": ("FILESYSTEM", "write"),
    "write_bytes": ("FILESYSTEM", "write"),
    "bind": ("NETWORK", "listen"),
    "listen": ("NETWORK", "listen"),
    "connect": ("NETWORK", "out"),
    "publish": ("NETWORK", "out"),   # MQTT/pub-sub outbound
}


@dataclass
class Capability:
    kind: str          # FILESYSTEM / NETWORK / ENV / SUBPROCESS / HARDWARE / IMPORT_PATH
    mode: str          # read / write / out / listen / exec / i2c / spi / uart / mutate
    detail: str        # human-readable evidence
    lineno: int
    scope: str = ""    # resource scope (path literal or expression hint)


@dataclass
class Findings:
    capabilities: list = field(default_factory=list)
    imports: set = field(default_factory=set)
    invariants: set = field(default_factory=set)
    smells: list = field(default_factory=list)   # (lineno, message)


def _dotted(node: ast.AST) -> Optional[str]:
    """Turn an ast.Attribute / ast.Name chain into an 'a.b.c' string."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return None


def _const(node: ast.AST):
    return node.value if isinstance(node, ast.Constant) else None


def _text(node: ast.AST) -> str:
    """Expression as readable text (for the path-scope hint)."""
    try:
        t = ast.unparse(node)
    except Exception:
        return "?"
    return t if len(t) <= 50 else t[:47] + "..."


class CapabilityVisitor(ast.NodeVisitor):
    def __init__(self):
        self.f = Findings()

    # --- imports ---
    def visit_Import(self, node):
        for alias in node.names:
            self.f.imports.add(alias.name.split(".")[0])
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self.f.imports.add(node.module.split(".")[0])
        self.generic_visit(node)

    # --- calls (effects) ---
    def visit_Call(self, node):
        dotted = _dotted(node.func)
        bare = dotted.split(".")[-1] if dotted else None
        kind = mode = evidence = None

        if dotted in CALL_SIGNATURES:
            kind, mode = CALL_SIGNATURES[dotted]; evidence = dotted
        elif bare in BARE_SIGNATURES:
            kind, mode = BARE_SIGNATURES[bare]; evidence = bare
        elif bare == "open":
            kind, mode = "FILESYSTEM", self._open_mode(node); evidence = "open"
        elif bare in METHOD_SIGNATURES and isinstance(node.func, ast.Attribute):
            kind, mode = METHOD_SIGNATURES[bare]; evidence = f".{bare}()"

        if kind:
            scope = self._fs_scope(node, dotted, bare) if kind == "FILESYSTEM" else ""
            self._add_capability(kind, mode, evidence, node, scope)

        # import-path mutation
        if dotted == "sys.path.append":
            self.f.capabilities.append(
                Capability("IMPORT_PATH", "mutate", "sys.path.append", node.lineno))

        # os.environ index / .get
        if dotted and dotted.startswith("os.environ"):
            self.f.capabilities.append(Capability("ENV", "read", dotted, node.lineno))

        self.generic_visit(node)

    def _add_capability(self, kind, mode, evidence, node, scope=""):
        cap = Capability(kind, mode, evidence, node.lineno, scope)
        self.f.capabilities.append(cap)
        # NETWORK listen -> host/port + smell
        if kind == "NETWORK" and mode == "listen" and evidence == "uvicorn.run":
            host = port = None
            for kw in node.keywords:
                if kw.arg == "host": host = _const(kw.value)
                if kw.arg == "port": port = _const(kw.value)
            if host is not None:
                cap.detail = f"uvicorn.run host={host} port={port}"
                if host in ("0.0.0.0", "::"):
                    self.f.smells.append(
                        (node.lineno, f"NETWORK listen on all interfaces (host={host}) - public exposure"))

    def _fs_scope(self, node, dotted, bare) -> str:
        """Extract the file scope (literal path or expression hint)."""
        pn = None
        if bare in ("open", "FileResponse") and node.args:
            pn = node.args[0]
        elif bare == "StaticFiles":
            pn = next((kw.value for kw in node.keywords if kw.arg == "directory"), None)
            if pn is None and node.args:
                pn = node.args[0]
        elif bare in ("read_text", "read_bytes", "write_text", "write_bytes") \
                and isinstance(node.func, ast.Attribute):
            pn = node.func.value
        elif dotted in ("os.remove", "os.unlink", "os.mkdir", "os.makedirs",
                        "shutil.rmtree", "shutil.copy", "shutil.move") and node.args:
            pn = node.args[0]
        if pn is None:
            return ""
        c = _const(pn)
        return c if isinstance(c, str) else _text(pn)

    def _open_mode(self, node) -> str:
        if len(node.args) >= 2:
            m = _const(node.args[1])
            if isinstance(m, str) and any(ch in m for ch in "wax+"):
                return "write"
        for kw in node.keywords:
            if kw.arg == "mode":
                m = _const(kw.value)
                if isinstance(m, str) and any(ch in m for ch in "wax+"):
                    return "write"
        return "read"

    # --- value invariants (noise filter) ---
    def visit_Compare(self, node):
        left = _dotted(node.left) or self._simple(node.left)
        if left:
            for op, comp in zip(node.ops, node.comparators):
                right = self._simple(comp)
                op_str = self._op(op)
                if right and op_str and self._meaningful(left, right):
                    self.f.invariants.add(f"{left} {op_str} {right}")
        self.generic_visit(node)

    @staticmethod
    def _meaningful(left: str, right: str) -> bool:
        # exclude dunders (e.g. __name__ == '__main__') and constant==constant
        if "__" in left or "__" in right:
            return False
        left_is_var = left[0].isalpha() or left[0] == "_"
        right_is_var = bool(right) and (right[0].isalpha() or right[0] == "_") \
            and not right.startswith("'")
        # at least one side should be a variable (not constant==constant)
        return left_is_var or right_is_var

    # --- smell: CORS allow_origins=["*"] ---
    def visit_keyword(self, node):
        if node.arg == "allow_origins" and isinstance(node.value, ast.List):
            for el in node.value.elts:
                if _const(el) == "*":
                    self.f.smells.append(
                        (getattr(node.value, "lineno", 0),
                         "CORS allow_origins=['*'] - any origin allowed"))
        self.generic_visit(node)

    def _simple(self, node):
        if isinstance(node, ast.Constant):
            return f"'{node.value}'" if isinstance(node.value, str) else str(node.value)
        return _dotted(node)

    def _op(self, op):
        return {ast.Eq: "==", ast.NotEq: "!=", ast.Lt: "<", ast.LtE: "<=",
                ast.Gt: ">", ast.GtE: ">="}.get(type(op))


# ---------------------------------------------------------------------------
# Constitution synthesis
# ---------------------------------------------------------------------------
STDLIB_IGNORE = {"sys", "os", "logging", "pathlib", "typing", "dataclasses",
                 "re", "json", "time", "datetime", "ast", "__future__", "math",
                 "hashlib", "base64", "collections", "functools", "io", "abc",
                 "enum", "threading", "socket", "struct", "random", "subprocess",
                 "shutil", "tempfile", "uuid", "copy", "itertools", "warnings",
                 "platform", "secrets", "urllib", "zipfile", "smtplib", "email",
                 "string", "asyncio", "webbrowser"}


def synthesize_bio(cell_name: str, f: Findings) -> str:
    grouped = {}
    for c in f.capabilities:
        grouped.setdefault((c.kind, c.mode), []).append(c)

    lines = [f"CELL {cell_name} {{", ""]
    lines.append("  # AUTO-SYNTHESIZED constitution  |  provenance: SYNTHESIZED (not ratified)")
    lines.append("  # The membrane is DENY-BY-DEFAULT: anything absent here is blocked at runtime.")
    lines.append("")
    lines.append("  CAPABILITIES {")
    if grouped:
        for (kind, mode), caps in sorted(grouped.items()):
            scopes = sorted({c.scope for c in caps if c.scope})
            no = sorted({c.lineno for c in caps})
            scope_txt = ("  scope: " + ", ".join(f'"{s}"' for s in scopes)) if scopes else ""
            lines.append(f"    {kind:<11} {mode:<7};   # line {no}{scope_txt}")
    else:
        lines.append("    # no effects detected")
    lines.append("    # everything else: DENY")
    lines.append("  }")
    lines.append("")

    deps = sorted(f.imports - STDLIB_IGNORE)
    if deps:
        lines.append("  DEPENDENCIES {")
        for d in deps:
            lines.append(f"    ALLOW {d};")
        lines.append("  }")
        lines.append("")

    if f.invariants:
        lines.append("  INVARIANTS {")
        for i, rule in enumerate(sorted(f.invariants), 1):
            lines.append(f"    RULE r{i}: {rule};")
        lines.append("  }")
        lines.append("")

    lines.append("}")
    return "\n".join(lines)


def analyze_file(path: str):
    with open(path, "r", encoding="utf-8") as fh:
        src = fh.read()
    v = CapabilityVisitor()
    v.visit(ast.parse(src))
    return v.f


def main():
    if len(sys.argv) < 2:
        print("Usage: python capability_analyzer.py <path>")
        sys.exit(1)
    path = sys.argv[1]
    f = analyze_file(path)
    cell = os.path.splitext(os.path.basename(path))[0].replace("-", "_")

    print("=" * 70)
    print(f"  CAPABILITY REPORT:  {path}")
    print("=" * 70)
    print("\n[EFFECTS]")
    if f.capabilities:
        for c in sorted(f.capabilities, key=lambda x: (x.kind, x.mode, x.lineno)):
            sc = f'  scope="{c.scope}"' if c.scope else ""
            print(f"  {c.kind:<11} {c.mode:<7} line {c.lineno:<4} {c.detail}{sc}")
    else:
        print("  (none)")

    print("\n[DEPENDENCIES]")
    print("  " + (", ".join(sorted(f.imports)) if f.imports else "(none)"))

    print("\n[VALUE-INVARIANT CANDIDATES]")
    print("  " + ("\n  ".join(sorted(f.invariants)) if f.invariants else "(none)"))

    print("\n[SMELLS / RISKS]")
    if f.smells:
        for ln, msg in sorted(f.smells):
            print(f"  ! line {ln}: {msg}")
    else:
        print("  (none)")

    print("\n" + "=" * 70)
    print("  SYNTHESIZED constitution.bio")
    print("=" * 70)
    bio = synthesize_bio(cell, f)
    print(bio)

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       f"{cell}.constitution.bio")
    with open(out, "w", encoding="utf-8") as oh:
        oh.write(bio + "\n")
    print(f"\n[OK] Constitution written: {out}")


if __name__ == "__main__":
    main()
