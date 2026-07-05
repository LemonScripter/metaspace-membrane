// A REAL (non-toy) log-analysis utility, compiled to wasm32-wasip1 and run under the
// MetaSpace WASI membrane. It does genuine work: it scans an input directory, reads every
// .log file, counts lines / errors / warnings, aggregates across files, ranks the noisiest
// file, and writes a report. It also attempts one thing outside its granted scope (reading a
// system file) — which the WASI capability model refuses.
//
// The point of the demo is not that this program is huge, but that it is REAL: real directory
// iteration, real parsing, real aggregation, real output — and its filesystem is bounded to
// exactly what the .bio grants (read /input, write /output), nothing else.

use std::collections::BTreeMap;
use std::fs::{self, File};
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};

#[derive(Default, Clone, Copy)]
struct Stats {
    lines: usize,
    errors: usize,
    warns: usize,
}

fn analyze(path: &Path) -> Stats {
    let mut s = Stats::default();
    if let Ok(f) = File::open(path) {
        for line in BufReader::new(f).lines().map_while(Result::ok) {
            s.lines += 1;
            let l = line.to_ascii_lowercase();
            if l.contains("error") {
                s.errors += 1;
            }
            if l.contains("warn") {
                s.warns += 1;
            }
        }
    }
    s
}

fn log_files(dir: &Path) -> Vec<PathBuf> {
    let mut v = Vec::new();
    if let Ok(entries) = fs::read_dir(dir) {
        for e in entries.flatten() {
            let p = e.path();
            if p.extension().map(|x| x == "log").unwrap_or(false) {
                v.push(p);
            }
        }
    }
    v.sort();
    v
}

fn main() {
    let input = Path::new("/input");
    let mut per_file: BTreeMap<String, Stats> = BTreeMap::new();
    let mut total = Stats::default();

    for p in log_files(input) {
        let s = analyze(&p);
        total.lines += s.lines;
        total.errors += s.errors;
        total.warns += s.warns;
        let name = p.file_name().unwrap().to_string_lossy().into_owned();
        per_file.insert(name, s);
    }

    // rank the noisiest file (most errors) — a bit of real aggregation logic
    let noisiest = per_file
        .iter()
        .max_by_key(|(_, s)| s.errors)
        .map(|(n, s)| format!("{} ({} errors)", n, s.errors))
        .unwrap_or_else(|| "none".into());

    if let Ok(mut out) = File::create("/output/report.txt") {
        let _ = writeln!(out, "LOG REPORT");
        for (name, s) in &per_file {
            let _ = writeln!(out, "{}: lines={} errors={} warns={}", name, s.lines, s.errors, s.warns);
        }
        let _ = writeln!(out, "NOISIEST: {}", noisiest);
        let _ = writeln!(
            out,
            "TOTAL: files={} lines={} errors={} warns={}",
            per_file.len(), total.lines, total.errors, total.warns
        );
    }

    println!(
        "processed files={} lines={} errors={} warns={} noisiest={}",
        per_file.len(), total.lines, total.errors, total.warns, noisiest
    );

    // attempt an effect OUTSIDE the grant: read a system file (no preopen -> refused by WASI)
    match fs::read_to_string("/etc/passwd") {
        Ok(_) => println!("LEAK: read /etc/passwd"),
        Err(e) => println!("contained: /etc/passwd refused ({})", e),
    }
}
