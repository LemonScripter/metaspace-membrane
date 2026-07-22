"""
mock_unleash.py
---------------
Minimal local Unleash server that speaks the standard unleash-client-go v4
protocol (./client/features, ./client/register, ./client/metrics).

It serves the FULL patched feature set from features_patched.json, so every
flag keeps its real value except `json-hooks-enabled`, whose `ide=jetski`
constraint we stripped -> the CLI's isFeatureEnabled() now returns TRUE.

Every request is logged to mock_unleash.log AND stdout, so we can empirically
confirm whether agy actually redirects to us (i.e. whether it honours
UNLEASH_URL). If we see a GET .../client/features hit, the redirect works.

Run:  python mock_unleash.py [port]     (default 4242)
"""
import json, os, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
FEATURES = os.path.join(HERE, "features_patched.json")
LOG = os.path.join(HERE, "mock_unleash.log")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 4242


def log(msg):
    line = f"{time.strftime('%H:%M:%S')} {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_features():
    with open(FEATURES, encoding="utf-8") as f:
        return f.read().encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body=b"", ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("ETag", '"mock-1"')
        self.end_headers()
        if body:
            self.wfile.write(body)

    def do_GET(self):
        log(f"GET  {self.path}  (from {self.client_address[0]})")
        if "features" in self.path:
            self._send(200, load_features())
        else:
            self._send(200, b'{"version":2,"features":[],"segments":[]}')

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        if n:
            self.rfile.read(n)
        log(f"POST {self.path}  (from {self.client_address[0]})")
        self._send(202, b"")

    def log_message(self, *a):
        pass  # we do our own logging


def main():
    if not os.path.exists(FEATURES):
        log(f"[!] {FEATURES} missing -- run build_features.py first")
        sys.exit(1)
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    log(f"[+] mock unleash listening on http://127.0.0.1:{PORT}  (serving {FEATURES})")
    log(f"[+] set  UNLEASH_URL = http://127.0.0.1:{PORT}/api   then launch agy")
    srv.serve_forever()


if __name__ == "__main__":
    main()
