#!/usr/bin/env python3
"""
Minimal HTML receiver. Accepts POST / with a bearer token and writes the body
to index.html. Nginx serves index.html statically.

Usage:
    CRAB_TOKEN=secret python server.py [--port 8765] [--out index.html]
"""

import argparse
import hmac
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def make_handler(token: str, path: Path):
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            auth = self.headers.get("Authorization", "")
            if not hmac.compare_digest(auth, f"Bearer {token}"):
                self.send_response(401)
                self.end_headers()
                return

            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)

            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)

            self.send_response(204)
            self.end_headers()
            print(f"Updated {path} ({len(body)} bytes)")

        def log_message(self, format, *args):
            pass  # silence default request logging

    return Handler


def main():
    token = os.environ.get("CRAB_TOKEN")
    if not token:
        print("Error: CRAB_TOKEN env var not set", file=sys.stderr)
        sys.exit(1)

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--path", type=Path, default=Path("index.html"))
    args = parser.parse_args()

    server = HTTPServer(("127.0.0.1", args.port), make_handler(token, args.path))
    print(f"Listening on 127.0.0.1:{args.port}, writing to {args.path}")
    server.serve_forever()


if __name__ == "__main__":
    main()
