#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MetaSpace Membrane — C-78 proof: a compromised WordPress plugin cannot write WordPress core.

The attacker model is the realistic one: the plugin is ALREADY running inside the PHP process.
No exploit is simulated and none is needed -- a compromised plugin simply is PHP code with the
same authority as WordPress itself. Nothing here depends on the language: the substrate does not
know what PHP is, which is the whole point of C-75 generalising.

Serving mode: the constitution grants writes under `wp-content/uploads/**` and nothing else,
because that is what a running WordPress actually writes. Plugin and theme UPDATES need a wider
maintenance scope and are out of scope for this claim.

LEGS
  * the same plugin run FREE first -- a differential control. Every attack must succeed there,
    or the confined zeros would only show that the probe never ran.
  * confined: core write, plugin-dir persistence, wp-config (credentials) and core deletion all
    refused; the granted uploads write still succeeds (positive control)
  * verified from outside, on two SEPARATE trees: the free tree's core is defaced, the confined
    tree's core is byte-for-byte intact. (An earlier version of this measurement shared one tree
    and therefore proved nothing about the outside state -- recorded here so it is not repeated.)
  * SCOPE-LIMIT, pinned mechanically: exec is NOT confined. Three routes -- shell_exec, exec and
    proc_open -- run identically confined and free. This leg asserts the limit still holds, so
    that the day C-79 lands this proof goes red and the ledger must be updated with it.

⚠ A measuring-instrument note that cost a run: the first version used `2>/dev/null` in the exec
probes. A redirect is a FILE WRITE, so Landlock refused it, the shell fell silent, and silence
was read as "exec blocked". The shell had in fact run and said so on the enforcer's stderr. The
exec probes now carry markers and no redirection: a missing answer is never evidence.

Linux + Landlock + php only; elsewhere prints PROOF_SKIPPED and exits 0.

Run:  python evidence/run_c78_wordpress_core_proof.py
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
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENFORCER = os.path.join(REPO, "products", "app_membrane", "sandbox_enforcer.py")

PLUGIN = r'''<?php
// A "feltort" plugin. Mar a PHP-folyamatban fut; nem kulso tamado.
$root = getenv('WP_ROOT');
$r = array();

function att(&$r, $name, $fn) {
    try { $r[$name] = $fn() ? 'DID' : 'FAILED'; }
    catch (Throwable $e) { $r[$name] = 'THREW'; }
}

// 1. CORE atirasa — a klasszikus backdoor-beultetes
att($r, 'write_core', function() use ($root) {
    return @file_put_contents($root . '/wp-includes/version.php', "<?php /* pwned */") !== false;
});
// 2. sajat maga alatti perzisztencia (uj plugin-fajl)
att($r, 'write_plugin_dir', function() use ($root) {
    return @file_put_contents($root . '/wp-content/plugins/evil/backdoor.php', "<?php") !== false;
});
// 3. wp-config.php — a hitelesito adatok
att($r, 'write_wpconfig', function() use ($root) {
    return @file_put_contents($root . '/wp-config.php', "<?php /* pwned */") !== false;
});
// 4. core torlese
att($r, 'delete_core', function() use ($root) {
    return @unlink($root . '/wp-admin/admin.php');
});
// 5. POZITIV KONTROLL: az uploads irasa — ezt az alkotmany ENGEDI
att($r, 'write_uploads', function() use ($root) {
    return @file_put_contents($root . '/wp-content/uploads/ok.txt', "legit") !== false;
});
// 6-7. EXEC. FIGYELEM: itt NINCS 2>/dev/null atiranyitas. Az atiranyitas FAJLIRAS,
// amit a Landlock megtagad — az elso meresben ettol NEMA lett a shell, es a probam
// a nemasagot "BLOCKED"-nak konyvelte, holott a shell lefutott. A hianyzo valasz
// sosem bizonyitek: a futas tenyet MARKERREL kell igazolni.
$out = @shell_exec('/bin/echo MARK_SHELL_EXEC');
$r['exec_shell'] = (is_string($out) && strpos($out, 'MARK_SHELL_EXEC') !== false)
    ? 'RAN' : 'NO_OUTPUT(' . var_export($out, true) . ')';
$o = array(); $rc = 255; @exec('/bin/echo MARK_EXEC_FUNC', $o, $rc);
$r['exec_func'] = (in_array('MARK_EXEC_FUNC', $o, true)) ? 'RAN:rc=' . $rc : 'NO_OUTPUT:rc=' . $rc;
// 8. a legdirektebb ut: proc_open, csovekkel (nem fajl)
$d = array(1 => array('pipe','w'));
$ph = @proc_open('/bin/echo MARK_PROC_OPEN', $d, $pipes);
if (is_resource($ph)) {
    $s = stream_get_contents($pipes[1]); fclose($pipes[1]); proc_close($ph);
    $r['exec_procopen'] = (strpos($s, 'MARK_PROC_OPEN') !== false) ? 'RAN' : 'NO_OUTPUT';
} else { $r['exec_procopen'] = 'REFUSED'; }

echo "WP_JSON=" . json_encode($r) . "\n";
'''


def build_tree():
    root = tempfile.mkdtemp(prefix="wp_")
    for d in ("wp-includes", "wp-admin", "wp-content/plugins/evil", "wp-content/uploads"):
        os.makedirs(os.path.join(root, *d.split("/")), exist_ok=True)
    for f, body in (("wp-includes/version.php", "<?php $wp_version='6.5';"),
                    ("wp-admin/admin.php", "<?php // core"),
                    ("wp-config.php", "<?php define('DB_PASSWORD','s3cret');")):
        with open(os.path.join(root, *f.split("/")), "w") as fh:
            fh.write(body)
    with open(os.path.join(root, "wp-content", "plugins", "evil", "evil.php"), "w") as fh:
        fh.write(PLUGIN)
    bio = os.path.join(root, "wp.bio")
    with open(bio, "w") as fh:
        fh.write('CELL WordPress {\n  CAPABILITIES {\n'
                 '    // serving mode: a running WordPress writes uploads, nothing else\n'
                 '    FILESYSTEM write "{{PROJECT_ROOT}}/wp-content/uploads/**";\n'
                 '  }\n}\n')
    return root, bio


def run(cmd, env):
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    m = re.search(r"WP_JSON=(\{.*\})", p.stdout or "")
    return (json.loads(m.group(1)) if m else {}), p


def main():
    if platform.system() != "Linux":
        print("PROOF_SKIPPED: not Linux")
        return 0
    php = shutil.which("php")
    if not php:
        print("PROOF_SKIPPED: no php on this machine")
        return 0
    sys.path.insert(0, os.path.join(REPO, "products", "app_membrane"))
    import sandbox_enforcer
    abi = sandbox_enforcer.landlock_abi()
    if abi < 1:
        print("PROOF_SKIPPED: no Landlock")
        return 0

    # KET KULON FA: az elso meresben kozos fat hasznaltam, igy a szabad futas mar
    # felulirta a core-t, mielott a bezart futas elindult — a kivulrol-ellenorzes
    # ettol ertelmetlen lett. Minden futas sajat, erintetlen fat kap.
    root_bare, bio_bare = build_tree()
    root, bio = build_tree()
    plugin_bare = os.path.join(root_bare, "wp-content", "plugins", "evil", "evil.php")
    plugin = os.path.join(root, "wp-content", "plugins", "evil", "evil.php")
    env = dict(os.environ)

    print("=" * 74)
    print("  C-78 — a compromised WordPress plugin cannot write WordPress core")
    print("=" * 74)
    print("  php          :", php)
    print("  Landlock ABI :", abi)
    print("  wp root      :", root)
    print("-" * 74)

    eb = dict(env); eb["WP_ROOT"] = root_bare
    bare, _ = run([php, plugin_bare], eb)
    ec = dict(env); ec["WP_ROOT"] = root
    conf, p2 = run([sys.executable, ENFORCER, "--bio", bio, "--root", root,
                    "--create-scopes", "--", php, plugin], ec)

    keys = ["write_core", "write_plugin_dir", "write_wpconfig", "delete_core",
            "write_uploads", "exec_shell", "exec_func", "exec_procopen"]
    print("  %-18s %-14s %s" % ("muvelet", "SZABADON", "SZUBSZTRATUM ALATT"))
    for k in keys:
        print("  %-18s %-14s %s" % (k, bare.get(k, "-"), conf.get(k, "-")))
    print("-" * 74)
    print("  enforcer:", (p2.stderr.strip().splitlines() or ["<none>"])[-1])
    cb = open(os.path.join(root_bare, "wp-includes", "version.php")).read()
    cc = open(os.path.join(root, "wp-includes", "version.php")).read()
    print("  core a SZABAD fan  :", cb[:40], "  -> pwned:", "pwned" in cb)
    print("  core a BEZART fan  :", cc[:40], "  -> pwned:", "pwned" in cc)
    print("  a bezart fa core-ja erintetlen:", "pwned" not in cc)
    print("=" * 74)
    print("-" * 74)
    fails = main_checks(bare, conf, cb, cc, p2)
    for d in (root, root_bare):
        shutil.rmtree(d, ignore_errors=True)
    print("=" * 74)
    if fails:
        print("  RESULT: FAIL — %d check(s)" % len(fails))
        for f in fails: print("    - " + f)
        return 1
    print("  RESULT: PASS — a compromised plugin could not touch WordPress core, its own")
    print("          directory, or wp-config; the granted uploads write still worked; and the")
    print("          exec limit is pinned, not glossed over.")
    return 0




def main_checks(bare, conf, cb, cc, p2):
    fails = []
    def ck(cond, msg):
        print("  [%s]  %s" % ("OK" if cond else "FAIL", msg))
        if not cond:
            fails.append(msg)
    ck("Landlock ABI" in (p2.stderr or ""), "enforcer applied Landlock (named in its own stderr)")
    ck(all(bare.get(k) == "DID" for k in
           ("write_core", "write_plugin_dir", "write_wpconfig", "delete_core")),
       "CONTROL - every attack succeeds when the plugin runs free")
    ck(conf.get("write_core") == "FAILED", "core write refused")
    ck(conf.get("write_plugin_dir") == "FAILED", "persistence in the plugin's own directory refused")
    ck(conf.get("write_wpconfig") == "FAILED", "wp-config.php (the credentials) refused")
    ck(conf.get("delete_core") == "FAILED", "core deletion refused")
    ck(conf.get("write_uploads") == "DID", "POSITIVE CONTROL - the granted uploads write succeeds")
    ck("pwned" in cb, "the free tree's core really was defaced")
    ck("pwned" not in cc, "the confined tree's core is intact, checked from outside")
    ck(all(str(conf.get(k, "")).startswith("RAN") for k in
           ("exec_shell", "exec_func", "exec_procopen")),
       "SCOPE-LIMIT pinned: exec is NOT confined (shell_exec / exec / proc_open all run) - C-79")
    return fails


if __name__ == "__main__":
    sys.exit(main())
