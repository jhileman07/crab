"""
Minimal HTML receiver. Accepts POST / with a bearer token and writes the body
to index.html. Nginx serves index.html statically.

Usage:
    CRAB_TOKEN=secret python server.py [--port 8765] [--out index.html] [-ttl TTL]
"""

import argparse
import gzip
import hmac
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def make_handler(token: str, path: Path, ttl: int):
    timer = None

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            nonlocal timer

            auth = self.headers.get("Authorization", "")
            if not hmac.compare_digest(auth, f"Bearer {token}"):
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                self.send_response(401)
                self.end_headers()
                return

            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            if self.headers.get("Content-Encoding") == "gzip":
                body = gzip.decompress(body)

            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)

            if timer:
                timer.cancel()
            if ttl > 0:
                timer = threading.Timer(ttl, lambda: path.write_bytes(b""))
                timer.daemon = True
                timer.start()

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
    parser.add_argument("--ttl", type=int, default=0, help="Seconds before clearing index.html (0=never)")
    args = parser.parse_args()

    server = HTTPServer(("127.0.0.1", args.port), make_handler(token, args.path, args.ttl))
    print(f"Listening on 127.0.0.1:{args.port}, writing to {args.path}")
    server.serve_forever()


if __name__ == "__main__":
    main()
