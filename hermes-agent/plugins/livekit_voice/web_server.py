#!/usr/bin/env python3
"""Lightweight HTTP server for LiveKit Voice Playground UI & Token Minting.

Runs on port 7885.
Provides:
- GET / : Serves gateway/livekit/web/index.html
- GET /api/token : Generates authenticated LiveKit JWT AccessToken for WebRTC room join.
"""

from __future__ import annotations

import json
import logging
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from livekit.api import AccessToken, VideoGrants

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("livekit-web")

WEB_DIR = Path(__file__).resolve().parent / "web"
LIVEKIT_API_KEY = "devkey"
LIVEKIT_API_SECRET = "secret"
LIVEKIT_WS_URL = "ws://localhost:7880"

class LiveKitWebHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/token":
            qs = parse_qs(parsed.query)
            identity = qs.get("identity", ["Boss"])[0]
            room = qs.get("room", ["maymint-room"])[0]

            token = AccessToken(api_key=LIVEKIT_API_KEY, api_secret=LIVEKIT_API_SECRET)
            token.with_identity(identity).with_name(identity).with_grants(
                VideoGrants(
                    room_join=True,
                    room=room,
                    can_publish=True,
                    can_subscribe=True,
                    can_publish_data=True
                )
            )
            jwt_token = token.to_jwt()

            resp = {
                "token": jwt_token,
                "url": LIVEKIT_WS_URL,
                "room": room,
                "identity": identity
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(resp).encode("utf-8"))
            return

        elif parsed.path == "/" or parsed.path == "":
            self.path = "/index.html"

        super().do_GET()

def main():
    port = 7885
    server = ThreadingHTTPServer(("0.0.0.0", port), LiveKitWebHandler)
    logger.info("🌸 Maymint LiveKit Web UI running at http://localhost:%d", port)
    server.serve_forever()

if __name__ == "__main__":
    main()
