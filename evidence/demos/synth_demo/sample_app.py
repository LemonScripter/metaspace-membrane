"""A tiny sample application, used only as INPUT to the synthesizer (never executed here).

Its real effects are what the synthesizer should detect:
  - reads a config file          -> FILESYSTEM read  "config.json"
  - writes a log file            -> FILESYSTEM write "logs/app.log"
  - fetches from an HTTP API      -> NETWORK out
It deliberately does NO subprocess, so the synthesized constitution must not grant one.
"""

import json
import requests


def run():
    with open("config.json") as f:            # FILESYSTEM read
        cfg = json.load(f)

    with open("logs/app.log", "w") as f:      # FILESYSTEM write
        f.write("started with %d keys" % len(cfg))

    requests.get("https://api.example.com/data")   # NETWORK out


if __name__ == "__main__":
    run()
