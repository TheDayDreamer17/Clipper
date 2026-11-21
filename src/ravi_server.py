import os
import sys
import json
import urllib.parse
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import http.server
import socketserver
import socket
from typing import Any

from src.portal_ui import (
    RAVI_PORTAL_HTML,
    get_ravi_candidate_clips,
    submit_ravi_feedback,
    search_stream_journals,
    get_stream_registry,
    rescan_stream,
    snip_moment
)

PORT = int(os.environ.get("RAVI_PORT", 3002))

class RaviStudioHandler(http.server.BaseHTTPRequestHandler):
    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path in ["/", "/index.html", "/portal/ravi", "/portal/ravi/"]:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
            self.end_headers()
            self.wfile.write(RAVI_PORTAL_HTML.encode("utf-8"))
            return

        elif path in ["/api/clips", "/portal/api/ravi/clips"]:
            clips = get_ravi_candidate_clips()
            self._send_json({"clips": clips})
            return

        elif path in ["/api/streams", "/portal/api/ravi/streams"]:
            self._send_json(get_stream_registry())
            return

        elif path in ["/api/journals", "/portal/api/ravi/journals"]:
            journal_dir = Path("docs/streams/ravi")
            sample_content = "No stream journal found."
            if journal_dir.exists():
                j_files = sorted(journal_dir.glob("session_*_journal.md"), reverse=True)
                if j_files:
                    try:
                        sample_content = j_files[0].read_text(encoding="utf-8")
                    except Exception:
                        pass
            self._send_json({"sample": sample_content[:15000]})
            return

        elif path.startswith("/video/"):
            rel_file = urllib.parse.unquote(path.replace("/video/", ""))
            file_path = Path("output") / rel_file
            if file_path.exists():
                self._serve_file(file_path, "video/mp4")
            else:
                self.send_error(404, "Video not found")
            return

        elif path.startswith("/training_candidates/"):
            rel_file = urllib.parse.unquote(path.lstrip("/"))
            file_path = Path("output") / rel_file
            if file_path.exists():
                self._serve_file(file_path, "video/mp4")
            else:
                self.send_error(404, "Video not found")
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            payload = {}

        if path in ["/api/feedback", "/portal/api/ravi/feedback"]:
            res = submit_ravi_feedback(payload)
            self._send_json(res)
            return

        elif path in ["/api/query", "/portal/api/ravi/query"]:
            q = payload.get("query", "")
            matches = search_stream_journals(q)
            self._send_json(matches)
            return

        elif path in ["/api/rescan", "/portal/api/ravi/rescan"]:
            res = rescan_stream(payload)
            self._send_json(res)
            return

        elif path in ["/api/snip", "/portal/api/ravi/snip"]:
            res = snip_moment(payload)
            self._send_json(res)
            return

        self.send_error(404, "Not Found")

    def _serve_file(self, file_path: Path, mime: str):
        try:
            chunk_size = 64 * 1024
            range_header = self.headers.get("Range")
            file_size = file_path.stat().st_size

            if range_header and range_header.startswith("bytes="):
                ranges = range_header[6:].split("-")
                start = int(ranges[0]) if ranges[0] else 0
                end = int(ranges[1]) if len(ranges) > 1 and ranges[1] else file_size - 1
                length = end - start + 1

                self.send_response(206)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_size}")
                self.send_header("Content-Length", str(length))
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()

                with open(file_path, "rb") as f:
                    f.seek(start)
                    bytes_remaining = length
                    while bytes_remaining > 0:
                        to_read = min(chunk_size, bytes_remaining)
                        data = f.read(to_read)
                        if not data:
                            break
                        self.wfile.write(data)
                        bytes_remaining -= len(data)
            else:
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(file_size))
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                with open(file_path, "rb") as f:
                    while True:
                        data = f.read(chunk_size)
                        if not data:
                            break
                        self.wfile.write(data)
        except Exception:
            pass

    def _send_json(self, data: Any):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

class DualStackServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    address_family = socket.AF_INET6
    daemon_threads = True

    def server_bind(self):
        try:
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        except Exception:
            pass
        super().server_bind()

def run_server(port: int = PORT):
    try:
        server = DualStackServer(("", port), RaviStudioHandler)
        print(f"🚀 Ravi Dedicated Studio running at http://localhost:{port} (and http://[::1]:{port})")
        server.serve_forever()
    except Exception as e:
        print(f"Fallback IPv4 binding on port {port} due to: {e}")
        fallback_server = socketserver.ThreadingMixIn, http.server.HTTPServer
        httpd = http.server.HTTPServer(("", port), RaviStudioHandler)
        print(f"🚀 Ravi Dedicated Studio (IPv4) running at http://localhost:{port}")
        httpd.serve_forever()

if __name__ == "__main__":
    run_server()
