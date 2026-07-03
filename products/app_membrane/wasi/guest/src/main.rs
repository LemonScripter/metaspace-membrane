// MetaSpace.Bio Engine Project — WASI guest (a realistic untrusted "app" -> wasm32-wasip1).
//
// A small report generator: it reads an input file, writes a processed output file, and also
// attempts two things it must NOT be able to do. This is a REAL compiled program with zero
// ambient filesystem authority. The host grants capabilities as WASI preopens derived from the
// .bio, WITH read/write granularity:
//   /input  is a READ_ONLY preopen   -> creating/writing a file here has no capability
//   /output is a READ_WRITE preopen  -> output is allowed
// Anything outside these preopens does not exist for the guest.

use std::fs::File;
use std::io::{Read, Write};

fn try_read(path: &str) {
    match File::open(path) {
        Ok(mut f) => {
            let mut s = String::new();
            let _ = f.read_to_string(&mut s);
            println!("READ  {} -> {:?}", path, s.trim());
        }
        Err(e) => println!("DENY  read {} ({})", path, e),
    }
}

fn try_write(path: &str, data: &[u8]) {
    match File::create(path) {
        Ok(mut f) => match f.write_all(data) {
            Ok(_) => println!("WROTE {}", path),
            Err(e) => println!("DENY  write {} ({})", path, e),
        },
        Err(e) => println!("DENY  write {} ({})", path, e),
    }
}

fn main() {
    // allowed: read the input (read-only preopen)
    try_read("/input/data.txt");
    // allowed: write the processed output (read-write preopen)
    try_write("/output/report.txt", b"processed report from input");
    // denied: writing into the READ_ONLY input preopen has no write capability
    try_write("/input/tamper.txt", b"tamper");
    // denied: no preopen for this path at all
    try_write("/etc/evil.txt", b"pwned");
}
