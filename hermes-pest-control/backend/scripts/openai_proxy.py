#!/usr/bin/env python3
"""
Proxy HTTP simple que redirige llamadas a api.openai.com.
Propósito: evitar que Hermes detecte la URL como 'api.openai.com' y fuerce
el modo codex_responses (Responses API), que no soporta gpt-4o-mini.
"""
import http.server
import urllib.request
import urllib.parse
import os
import sys
import json

TARGET = "https://api.openai.com"
PORT = int(os.environ.get("OPENAI_PROXY_PORT", "18123"))
API_KEY = os.environ.get("OPENAI_API_KEY", "")


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Silenciar logs

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.end_headers()

    def _proxy(self):
        url = f"{TARGET}{self.path}"
        body_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(body_len) if body_len else b""

        headers = {
            "Content-Type": self.headers.get("Content-Type", "application/json"),
        }
        # Pasar la Authorization del cliente (Hermes ya la pone)
        auth = self.headers.get("Authorization")
        if auth:
            headers["Authorization"] = auth
        elif API_KEY:
            headers["Authorization"] = f"Bearer {API_KEY}"

        req = urllib.request.Request(url, data=body or None, headers=headers, method=self.command)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                self.send_response(resp.status)
                for k, v in resp.headers.items():
                    if k.lower() not in ("transfer-encoding", "connection"):
                        self.send_header(k, v)
                self.end_headers()
                self.wfile.write(resp.read())
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as ex:
            self.send_response(502)
            self.end_headers()
            self.wfile.write(str(ex).encode())

    do_GET = _proxy
    do_POST = _proxy
    do_PUT = _proxy
    do_DELETE = _proxy
    do_PATCH = _proxy


if __name__ == "__main__":
    server = http.server.HTTPServer(("127.0.0.1", PORT), ProxyHandler)
    print(f"OpenAI proxy en http://127.0.0.1:{PORT} → {TARGET}", flush=True)
    server.serve_forever()
