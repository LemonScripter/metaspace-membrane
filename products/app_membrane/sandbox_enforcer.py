#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace Membrane — SandboxEnforcer: a `.bio` -> Linux Landlock OS-sandbox (Product A).

Confines a REAL native program (any language, any binary) to the filesystem effects its
constitution allows, enforced by the kernel (Landlock LSM), not by the program's cooperation.

MVP SCOPE — WRITE confinement (stated plainly):
  The Landlock ruleset governs only filesystem-*modifying* operations (create / write / delete /
  rename / make-node). It grants them ONLY beneath the `.bio`'s FILESYSTEM write scopes; a write
  anywhere else fails with EACCES at the kernel. READ and EXECUTE are left unrestricted, so any
  dynamically-linked program still starts and runs normally. Read/execute confinement is also a
  Landlock capability and is deferred here (it needs the program's runtime deps enumerated).
  This is the "contain effects" thesis at the OS level: a program can only *change* the world
  where its constitution says it may.

PLATFORM: Linux with the Landlock LSM (kernel >= 5.13; ABI auto-detected). x86_64 / aarch64.
FAIL-CLOSED: if Landlock is unavailable, the enforcer REFUSES to launch — it will never run a
program unconfined while claiming to confine it.

CLI:
    python sandbox_enforcer.py --bio app.bio --root /proj -- <program> [args...]
    python sandbox_enforcer.py --write /proj/out -- <program> [args...]
"""

import os
import sys
import shutil
import ctypes
import struct
import platform
import argparse

# syscall numbers (identical on x86_64 and aarch64)
_NR = {"x86_64": (444, 445, 446), "aarch64": (444, 445, 446)}
_LANDLOCK_CREATE_RULESET_VERSION = 1
_LANDLOCK_RULE_PATH_BENEATH = 1
_PR_SET_NO_NEW_PRIVS = 38

# landlock_access_fs bits (uapi/linux/landlock.h)
_FS = {
    "EXECUTE": 1 << 0, "WRITE_FILE": 1 << 1, "READ_FILE": 1 << 2, "READ_DIR": 1 << 3,
    "REMOVE_DIR": 1 << 4, "REMOVE_FILE": 1 << 5, "MAKE_CHAR": 1 << 6, "MAKE_DIR": 1 << 7,
    "MAKE_REG": 1 << 8, "MAKE_SOCK": 1 << 9, "MAKE_FIFO": 1 << 10, "MAKE_BLOCK": 1 << 11,
    "MAKE_SYM": 1 << 12, "REFER": 1 << 13, "TRUNCATE": 1 << 14,
}


def _libc():
    return ctypes.CDLL(None, use_errno=True)


def landlock_abi():
    """Return the supported Landlock ABI version (>=1), or 0 if Landlock is unavailable."""
    if platform.system() != "Linux" or platform.machine() not in _NR:
        return 0
    try:
        libc = _libc()
        v = libc.syscall(ctypes.c_long(_NR[platform.machine()][0]),
                         ctypes.c_void_p(0), ctypes.c_size_t(0),
                         ctypes.c_uint(_LANDLOCK_CREATE_RULESET_VERSION))
        return int(v) if v and v > 0 else 0
    except Exception:
        return 0


def _write_access_mask(abi):
    bits = (_FS["WRITE_FILE"] | _FS["REMOVE_DIR"] | _FS["REMOVE_FILE"] | _FS["MAKE_CHAR"] |
            _FS["MAKE_DIR"] | _FS["MAKE_REG"] | _FS["MAKE_SOCK"] | _FS["MAKE_FIFO"] |
            _FS["MAKE_BLOCK"] | _FS["MAKE_SYM"])
    if abi >= 2:
        bits |= _FS["REFER"]
    if abi >= 3:
        bits |= _FS["TRUNCATE"]
    return bits


# Directories the dynamic loader needs to map executable pages from. Without EXECUTE on
# these, a dynamically-linked program cannot start at all -- which is exactly why the MVP
# left EXECUTE unhandled rather than half-handled.
_RUNTIME_EXEC_DIRS = ("/lib", "/lib64", "/usr/lib", "/usr/lib64", "/usr/libexec")


def runtime_exec_paths(program):
    """The minimum set that must stay executable for `program` to run at all: the program
    file itself, plus the loader/library directories.

    The program is granted as a FILE, not as its directory. That distinction is the whole
    mechanism here: on a merged-/usr Debian both `php` and `sh` live under /usr/bin, so
    granting the directory would grant the shell too and the confinement would be theatre."""
    paths = []
    p = shutil.which(program) or program
    if os.path.exists(p):
        paths.append(os.path.realpath(p))
    for d in _RUNTIME_EXEC_DIRS:
        if os.path.isdir(d):
            paths.append(d)
    return sorted(set(paths))


def bio_exec_paths(bio_text, root):
    """Programs the constitution explicitly grants, from `SUBPROCESS exec "..."`.

    No new .bio vocabulary is introduced: SUBPROCESS/exec is an existing capability kind, so
    the provenance fingerprint is unchanged and O-3 does not arise."""
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from core.guard import parse_capabilities
    out = []
    for kind, mode, scopes in parse_capabilities(bio_text):
        if kind == "SUBPROCESS" and mode == "exec":
            for s in scopes:
                s = s.replace("{{PROJECT_ROOT}}", root)
                p = shutil.which(s) or s
                if os.path.exists(p):
                    out.append(os.path.realpath(p))
    return sorted(set(out))


def confine_writes(write_dirs, exec_paths=None):
    """Apply a Landlock ruleset to the CURRENT process so that only `write_dirs` (and paths
    beneath them) are writable; all other filesystem-modifying operations are denied by the
    kernel. Returns the ABI version used. Raises OSError if Landlock is unavailable / a syscall
    fails.

    `exec_paths` is opt-in (None = the historical behaviour, EXECUTE unhandled and therefore
    unrestricted). When given, EXECUTE joins the handled set, so execution is denied everywhere
    except beneath those paths -- and each rule now carries its OWN access set rather than the
    whole handled mask, or granting a writable directory would silently grant execution in it."""
    abi = landlock_abi()
    if abi < 1:
        raise OSError("Landlock unavailable (need Linux kernel >= 5.13 with the landlock LSM)")
    arch = platform.machine()
    nr_create, nr_add, nr_restrict = _NR[arch]
    libc = _libc()
    write_bits = _write_access_mask(abi)
    exec_bits = _FS["EXECUTE"] if exec_paths is not None else 0
    handled = write_bits | exec_bits

    # landlock_ruleset_attr { __u64 handled_access_fs; }  (size 8 governs FS only)
    attr = struct.pack("<Q", handled)
    abuf = ctypes.create_string_buffer(attr, len(attr))
    rs = libc.syscall(ctypes.c_long(nr_create), ctypes.c_void_p(ctypes.addressof(abuf)),
                      ctypes.c_size_t(len(attr)), ctypes.c_uint(0))
    if rs < 0:
        e = ctypes.get_errno()
        raise OSError(e, "landlock_create_ruleset: " + os.strerror(e))
    rs = int(rs)
    def _add(path, bits):
        fd = os.open(path, os.O_PATH | os.O_CLOEXEC)
        try:
            # landlock_path_beneath_attr { __u64 allowed_access; __s32 parent_fd; } packed=12
            pb = struct.pack("<Qi", bits, fd)
            pbuf = ctypes.create_string_buffer(pb, len(pb))
            r = libc.syscall(ctypes.c_long(nr_add), ctypes.c_int(rs),
                             ctypes.c_uint(_LANDLOCK_RULE_PATH_BENEATH),
                             ctypes.c_void_p(ctypes.addressof(pbuf)), ctypes.c_uint(0))
            if r < 0:
                e = ctypes.get_errno()
                raise OSError(e, "landlock_add_rule(%s): %s" % (path, os.strerror(e)))
        finally:
            os.close(fd)

    try:
        for d in write_dirs:
            _add(d, write_bits)
        for p in (exec_paths or []):
            _add(p, exec_bits)
        # PR_SET_NO_NEW_PRIVS is required before restrict_self
        if libc.prctl(ctypes.c_int(_PR_SET_NO_NEW_PRIVS), ctypes.c_ulong(1),
                      ctypes.c_ulong(0), ctypes.c_ulong(0), ctypes.c_ulong(0)) != 0:
            e = ctypes.get_errno()
            raise OSError(e, "prctl(NO_NEW_PRIVS): " + os.strerror(e))
        r = libc.syscall(ctypes.c_long(nr_restrict), ctypes.c_int(rs), ctypes.c_uint(0))
        if r < 0:
            e = ctypes.get_errno()
            raise OSError(e, "landlock_restrict_self: " + os.strerror(e))
    finally:
        os.close(rs)
    return abi


def bio_write_dirs(bio_text, root, create=False):
    """Extract the directories named by the FILESYSTEM write scopes of a .bio constitution.

    With `create=True` a declared scope whose directory does not exist yet is created rather
    than skipped. Skipping is a silent over-restriction: the constitution grants the program
    an output directory, the ruleset never mentions it, and the program simply cannot write
    where its own `.bio` says it may."""
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from core.guard import parse_capabilities
    dirs = []
    for kind, mode, scopes in parse_capabilities(bio_text):
        if kind == "FILESYSTEM" and mode == "write":
            for s in scopes:
                s = s.replace("{{PROJECT_ROOT}}", root)
                for suf in ("/**", "/*", "**", "*"):
                    if s.endswith(suf):
                        s = s[:-len(suf)]
                        break
                s = s.rstrip("/") or "/"
                if create and not os.path.isdir(s):
                    try:
                        os.makedirs(s, exist_ok=True)
                    except OSError as e:
                        sys.stderr.write("[SANDBOX] could not create granted scope %s (%s); "
                                         "it stays outside the ruleset.\n" % (s, e))
                if os.path.isdir(s):
                    dirs.append(os.path.abspath(s))
    return sorted(set(dirs))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="sandbox_enforcer",
                                 description="Confine a program's filesystem writes to a .bio via Landlock.")
    ap.add_argument("--bio", help="constitution; its FILESYSTEM write scopes become writable dirs")
    ap.add_argument("--root", default=os.getcwd(), help="value substituted for {{PROJECT_ROOT}}")
    ap.add_argument("--write", action="append", default=[], help="an extra writable dir (repeatable)")
    ap.add_argument("--create-scopes", action="store_true",
                    help="create a declared write scope whose directory does not exist yet, instead of silently dropping it")
    ap.add_argument("--confine-exec", action="store_true",
                    help="also confine EXECUTE: only the program itself, the runtime\n"
                         "libraries and the .bio's SUBPROCESS exec grants may be executed")
    ap.add_argument("cmd", nargs=argparse.REMAINDER, help="-- <program> [args...]")
    args = ap.parse_args(argv)

    write_dirs = [os.path.abspath(d) for d in args.write if os.path.isdir(d)]
    if args.bio:
        with open(args.bio, encoding="utf-8") as fh:
            write_dirs += bio_write_dirs(fh.read(), args.root, create=args.create_scopes)
    write_dirs = sorted(set(write_dirs))

    cmd = args.cmd
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        sys.stderr.write("no program given (use: ... -- <program> [args])\n")
        return 2

    exec_paths = None
    if args.confine_exec:
        exec_paths = runtime_exec_paths(cmd[0])
        if args.bio:
            with open(args.bio, encoding="utf-8") as fh:
                exec_paths += bio_exec_paths(fh.read(), args.root)
        exec_paths = sorted(set(exec_paths))
        if not any(os.path.isfile(p) for p in exec_paths):
            sys.stderr.write("[SANDBOX] fail-closed: could not locate %r to grant it EXECUTE "
                             "-> refusing (the program could not start anyway).\n" % cmd[0])
            return 3

    if landlock_abi() < 1:
        sys.stderr.write("[SANDBOX] fail-closed: Landlock unavailable -> refusing to launch "
                         "(will not run a program unconfined).\n")
        return 3
    try:
        abi = confine_writes(write_dirs, exec_paths)
    except OSError as e:
        sys.stderr.write("[SANDBOX] fail-closed: could not apply Landlock (%s) -> refusing.\n" % e)
        return 3
    sys.stderr.write("[SANDBOX] Landlock ABI v%d: writes confined to %s\n" % (abi, write_dirs))
    if exec_paths is not None:
        sys.stderr.write("[SANDBOX] EXECUTE confined to %s\n" % exec_paths)
    try:
        os.execvp(cmd[0], cmd)
    except OSError as e:
        sys.stderr.write("[SANDBOX] exec failed: %s\n" % e)
        return 127


if __name__ == "__main__":
    sys.exit(main())
