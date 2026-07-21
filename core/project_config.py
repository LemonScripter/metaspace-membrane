#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Per-project constitutions, stored USER-LEVEL under ~/.claude/metaspace.

This is how "settings per working directory" coexists with the self-protection property: each
working directory can have its own constitution + mode, but ALL of them live under ~/.claude
(outside any project's write scope), so a deceived agent still cannot read... er, cannot WRITE
them (the constitution denies writes to {{CLAUDE_HOME}}/**). One source of truth for the hook
(which resolves a project's config at runtime) and the UI/CLI (which edit it).

Layout:
    ~/.claude/metaspace/
        session.constitution.bio      # the user-level default (from `metaspace install`)
        registry.json                 # { "<abs project path>": {hash, mode, label} }
        projects/<hash>.bio           # a per-project constitution

Zero third-party dependencies (stdlib only), like the rest of the Warden hot path.
"""

import os
import json
import hashlib


def home_ms():
    return os.path.join(os.path.expanduser("~"), ".claude", "metaspace")


def projects_dir():
    return os.path.join(home_ms(), "projects")


def defaults_path():
    return os.path.join(home_ms(), "config.json")


def load_defaults():
    """User-level defaults (mode, constitution path) read from DISK, not from the environment.

    Why this exists (O-13, measured 2026-07-21): `metaspace install` records the mode and the
    constitution path in the `env` block of ~/.claude/settings.json, and Claude Code injects
    those into the hook process. **Cursor does not** — it invokes the same hook but propagates
    no env, so the hook silently fell back to its built-in defaults: enforcing instead of the
    configured observe-mode, and the SHIPPED constitution instead of the user's own. A host that
    honours the hook but not the env block must not quietly get different rules, so the settings
    are mirrored to a file every host can read.
    """
    p = defaults_path()
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as fh:
                d = json.load(fh)
            if isinstance(d, dict):
                return d
        except Exception:
            pass
    return {}


def save_defaults(mode=None, bio=None):
    """Merge-write the user-level defaults. Never raises; config is not the hot path."""
    try:
        d = load_defaults()
        if mode is not None:
            d["mode"] = str(mode).lower()
        if bio is not None:
            d["bio"] = str(bio).replace("\\", "/")
        os.makedirs(home_ms(), exist_ok=True)
        with open(defaults_path(), "w", encoding="utf-8") as fh:
            json.dump(d, fh, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def registry_path():
    return os.path.join(home_ms(), "registry.json")


def norm(path):
    return os.path.normpath(os.path.abspath(path)).replace("\\", "/")


def project_hash(path):
    return hashlib.sha1(norm(path).encode("utf-8")).hexdigest()[:16]


def load_registry():
    p = registry_path()
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return {}
    return {}


def save_registry(reg):
    os.makedirs(home_ms(), exist_ok=True)
    with open(registry_path(), "w", encoding="utf-8") as fh:
        json.dump(reg, fh, indent=2, ensure_ascii=False)


def resolve(project_root, default_bio=None, default_mode="enforce"):
    """Resolve (bio_path, mode) for a project: its own registered config if present and the
    constitution file exists, else the supplied defaults. Never raises."""
    try:
        entry = load_registry().get(norm(project_root))
        if entry:
            bio_path = os.path.join(projects_dir(), str(entry.get("hash")) + ".bio")
            if os.path.exists(bio_path):
                return bio_path, str(entry.get("mode", default_mode)).lower()
    except Exception:
        pass
    return default_bio, default_mode


def bio_path_for(project_root):
    return os.path.join(projects_dir(), project_hash(project_root) + ".bio")


def set_project(project_root, bio_text, mode="dryrun", label=None):
    """Create/update a project's constitution (under ~/.claude) and its registry entry."""
    npath = norm(project_root)
    h = project_hash(npath)
    os.makedirs(projects_dir(), exist_ok=True)
    with open(os.path.join(projects_dir(), h + ".bio"), "w", encoding="utf-8") as fh:
        fh.write(bio_text)
    reg = load_registry()
    reg[npath] = {"hash": h, "mode": str(mode).lower(),
                  "label": label or os.path.basename(npath) or npath}
    save_registry(reg)
    return h


def set_mode(project_root, mode):
    reg = load_registry()
    entry = reg.get(norm(project_root))
    if not entry:
        return False
    entry["mode"] = str(mode).lower()
    save_registry(reg)
    return True


def read_bio(project_root):
    p = bio_path_for(project_root)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            return fh.read()
    return None


def remove_project(project_root):
    npath = norm(project_root)
    reg = load_registry()
    entry = reg.pop(npath, None)
    if entry:
        try:
            os.remove(os.path.join(projects_dir(), str(entry.get("hash")) + ".bio"))
        except OSError:
            pass
        save_registry(reg)
    return entry is not None


def list_projects():
    """-> list of {path, hash, mode, label} for the UI/CLI."""
    out = []
    for path, e in sorted(load_registry().items()):
        out.append({"path": path, "hash": e.get("hash"),
                    "mode": e.get("mode", "enforce"), "label": e.get("label", path)})
    return out
