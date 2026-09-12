#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace Membrane — C-79 proof: a confined process can execute only the programs its
constitution grants, and a granted shell cannot launder an ungranted one.

WHERE THIS COMES FROM. C-78 proved a compromised WordPress plugin cannot write core, and
pinned the limit that it could still exec freely: `shell_exec`, `exec` and `proc_open` all ran
under the substrate exactly as they did free. This closes that half.

THE MECHANISM, and why it is not merely a flag. Landlock's EXECUTE access must join the handled
set for execution to be restricted at all -- and then the confined program must still start
itself and map its own shared libraries. Three consequences:

  * each rule carries its OWN access set. Previously every rule got the whole handled mask, so
    turning EXECUTE on would have granted execution inside the WRITABLE directory -- which for
    WordPress is `wp-content/uploads`, precisely where an attacker uploads.
  * the program is granted as a FILE, not as its directory. On a merged-/usr Debian `php` and
    `sh` both live under /usr/bin; granting the directory would grant the shell and the
    confinement would be theatre.
  * the loader directories keep EXECUTE, or nothing dynamically linked starts at all.

FOUR LEGS. The middle two are the interesting ones, and they exist because the first version of
this proof could not tell two failures apart: "the shell never started" and "the shell started
but the program it then ran was refused" both look like empty output. A shell BUILTIN needs no
second exec, so it separates them.

  A  free                    every attack works; without this the zeros below prove nothing
  B  confined, no grant      php STILL STARTS (load-bearing: otherwise the approach is wrong,
                             not strict), writes refused, and no exec of any kind
  C  + `SUBPROCESS exec "/bin/sh"`
                             the shell itself now runs (builtin proves it) -- BUT
                             `/bin/echo` is still refused, so a granted shell cannot be used
                             to launder an ungranted program
  D  + `/bin/sh` and `/bin/echo`
                             the full chain returns: the allowlist is an allowlist

Linux + Landlock + php only; elsewhere PROOF_SKIPPED, exit 0.

Run:  python evidence/run_c79_exec_proof.py
"""

import os
import re
import sys
import json
import shutil
import tempfile
import platform
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ENFORCER = os.path.join(REPO, "products", "app_membrane", "sandbox_enforcer.py")

PROBE = r'''<?php
$root = getenv('WP_ROOT'); $r = array();
$r['php_started'] = true;
$r['write_core'] = @file_put_contents($root.'/wp-includes/version.php', "<?php /* pwned */") !== false ? 'DID' : 'FAILED';
$r['write_uploads'] = @file_put_contents($root.'/wp-content/uploads/ok.txt', "legit") !== false ? 'DID' : 'FAILED';

// BUILTIN: dash runs `echo` internally, so ONLY the shell is exec'd, nothing after it.
// This is what separates "the shell never started" from "the shell started but the
// program it then ran was refused" -- both of which otherwise look like empty output.
$ob = @shell_exec('echo MARK_BUILTIN');
$r['exec_builtin'] = (is_string($ob) && strpos($ob,'MARK_BUILTIN') !== false) ? 'RAN' : 'BLOCKED';

$out = @shell_exec('/bin/echo MARK_SHELL');
$r['exec_shell'] = (is_string($out) && strpos($out,'MARK_SHELL') !== false) ? 'RAN' : 'BLOCKED';
$o = array(); $rc = 255; @exec('/bin/echo MARK_EXEC', $o, $rc);
$r['exec_func'] = in_array('MARK_EXEC', $o, true) ? 'RAN' : 'BLOCKED';
$d = array(1 => array('pipe','w'));
$ph = @proc_open('/bin/echo MARK_PROC', $d, $pipes);
if (is_resource($ph)) {
    $s = stream_get_contents($pipes[1]); fclose($pipes[1]); proc_close($ph);
    $r['exec_procopen'] = strpos($s,'MARK_PROC') !== false ? 'RAN' : 'BLOCKED';
} else { $r['exec_procopen'] = 'BLOCKED'; }
echo "C79_JSON=".json_encode($r)."\n";
'''

BIO_HEAD = 'CELL WordPress {\n  CAPABILITIES {\n    FILESYSTEM write "{{PROJECT_ROOT}}/wp-content/uploads/**";\n'
BIO_TAIL = '  }\n}\n'


def build(grants=()):
    root = tempfile.mkdtemp(prefix="c79_")
    for d in ("wp-includes", "wp-content/uploads"):
        os.makedirs(os.path.join(root, *d.split("/")), exist_ok=True)
    with open(os.path.join(root, "wp-includes", "version.php"), "w") as f:
        f.write("<?php $wp_version='6.5';")
    probe = os.path.join(root, "probe.php")
    with open(probe, "w") as f:
        f.write(PROBE)
    bio = os.path.join(root, "wp.bio")
    lines = "".join('    SUBPROCESS exec "%s";\n' % g for g in grants)
    with open(bio, "w") as f:
        f.write(BIO_HEAD + lines + BIO_TAIL)
    return root, bio, probe


def run(cmd, root):
    env = dict(os.environ)
    env["WP_ROOT"] = root
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    m = re.search(r"C79_JSON=(\{.*\})", p.stdout or "")
    return (json.loads(m.group(1)) if m else {}), p


def confined(php, grants):
    root, bio, probe = build(grants)
    res, p = run([sys.executable, ENFORCER, "--bio", bio, "--root", root,
                  "--create-scopes", "--confine-exec", "--", php, probe], root)
    return root, res, p


def main():
    if platform.system() != "Linux":
        print("PROOF_SKIPPED: not Linux")
        return 0
    php = shutil.which("php")
    if not php:
        print("PROOF_SKIPPED: no php")
        return 0
    sys.path.insert(0, os.path.join(REPO, "products", "app_membrane"))
    import sandbox_enforcer
    abi = sandbox_enforcer.landlock_abi()
    if abi < 1:
        print("PROOF_SKIPPED: no Landlock")
        return 0

    ra, ba, pa = build()
    A, _ = run([php, pa], ra)
    rb, B, pB = confined(php, ())
    rc, C, pC = confined(php, ("/bin/sh",))
    rd, D, pD = confined(php, ("/bin/sh", "/bin/echo"))

    keys = ("php_started", "write_core", "write_uploads", "exec_builtin",
            "exec_shell", "exec_func", "exec_procopen")
    print("=" * 78)
    print("  C-79 — a confined process executes only what its constitution grants")
    print("=" * 78)
    print("  Landlock ABI :", abi, " php:", php)
    print("-" * 78)
    print("  %-15s %-9s %-12s %-11s %s" % ("", "A free", "B no grant", "C +sh", "D +sh +echo"))
    for k in keys:
        print("  %-15s %-9s %-12s %-11s %s"
              % (k, A.get(k, "-"), B.get(k, "-"), C.get(k, "-"), D.get(k, "-")))
    print("-" * 78)
    for tag, p in (("B", pB), ("C", pC), ("D", pD)):
        for line in (p.stderr or "").strip().splitlines():
            if "EXECUTE" in line:
                print("  %s: %s" % (tag, line))
    print("-" * 78)

    fails = []

    def ck(cond, msg):
        print("  [%s]  %s" % ("OK" if cond else "FAIL", msg))
        if not cond:
            fails.append(msg)

    ck(all(A.get(k) == "RAN" for k in ("exec_builtin", "exec_shell", "exec_func", "exec_procopen"))
       and A.get("write_core") == "DID",
       "CONTROL - free: every exec route runs and the core write succeeds")
    ck(B.get("php_started") is True,
       "LOAD-BEARING: php still STARTS under EXECUTE confinement (strict, not broken)")
    ck(B.get("write_core") == "FAILED", "confined: the core write is still refused")
    ck(B.get("write_uploads") == "DID", "confined: the GRANTED write still works")
    ck(all(B.get(k) == "BLOCKED" for k in
           ("exec_builtin", "exec_shell", "exec_func", "exec_procopen")),
       "confined, no grant: nothing executes at all - not even the shell itself")
    ck(C.get("exec_builtin") == "RAN",
       "POSITIVE CONTROL: granting /bin/sh makes the SHELL run (a builtin needs no second "
       "exec), so B is an allowlist and not a failure to start")
    ck(C.get("exec_shell") == "BLOCKED" and C.get("exec_func") == "BLOCKED",
       "AND a granted shell cannot LAUNDER an ungranted program: /bin/echo stays refused")
    ck(D.get("exec_shell") == "RAN" and D.get("exec_func") == "RAN"
       and D.get("exec_procopen") == "RAN",
       "granting both /bin/sh and /bin/echo brings the whole chain back")
    ck(all(x.get("write_core") == "FAILED" for x in (B, C, D)),
       "granting exec never loosens the WRITE confinement (per-rule access sets)")

    for d in (ra, rb, rc, rd):
        shutil.rmtree(d, ignore_errors=True)
    print("=" * 78)
    if fails:
        print("  RESULT: FAIL — %d check(s)" % len(fails))
        for f in fails:
            print("    - " + f)
        if (pB.stderr or "").strip():
            sys.stderr.write("---- B stderr ----\n" + pB.stderr.strip()[-1200:] + "\n")
        return 1
    print("  RESULT: PASS — nothing executes but what the constitution grants; the confined")
    print("          program still starts itself; a granted shell cannot smuggle an ungranted")
    print("          program past the rule; and the write boundary is untouched throughout.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
