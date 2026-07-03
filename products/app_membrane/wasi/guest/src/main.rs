// MetaSpace.Bio Engine Project — WASI guest (an untrusted "app" compiled to wasm32-wasip1).
//
// This is a REAL compiled program, not hand-written WAT. It runs under WASI with zero
// ambient filesystem authority: it can only touch directories the host preopens. The host
// derives the preopen set from the .bio constitution. Any path outside the granted sandbox
// has no capability, so the open fails — there is no ambient path to escape through.

use std::fs::File;
use std::io::Write;

fn attempt(path: &str, data: &[u8]) {
    match File::create(path) {
        Ok(mut f) => match f.write_all(data) {
            Ok(_) => println!("WROTE {}", path),
            Err(e) => println!("DENY  {} (write error: {})", path, e),
        },
        Err(e) => println!("DENY  {} (open error: {})", path, e),
    }
}

fn main() {
    // in-scope: inside the granted sandbox preopen -> allowed
    attempt("/sandbox/app_output.txt", b"guest wrote this");
    // out of scope: no preopen for this path -> no capability -> denied
    attempt("/etc/evil.txt", b"pwned");
    // traversal attempt: WASI resolves within the preopen and refuses to escape
    attempt("/sandbox/../escape.txt", b"exfil");
}
