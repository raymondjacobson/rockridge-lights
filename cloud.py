"""Puts the control panel on the internet, through the rockridge-lights Worker on Cloudflare.

The panel keeps a WebSocket open to the Worker (it only ever connects out, so nothing at home
is opened up). The Worker passes along each API call a browser makes, and this runs it through
the panel's own Flask app and sends back the answer. While anyone has the page open, it also
sends the panel's live stream (state and frames). The messages are listed in cloud/src/link.ts.

It's on when ~/.config/rockridge-lights/cloud.env has LIGHTS_CLOUD_URL and LIGHTS_DEVICE_TOKEN
(scripts/pair-device.sh writes them). Needs the websocket-client package.
"""
import base64
import json
import os
import threading
import time
import traceback
from pathlib import Path

CONFIG = Path.home() / ".config" / "rockridge-lights" / "cloud.env"
CHUNK = 256 * 1024  # body bytes per message
PING_SECONDS = 25


def settings():
    """(url, token) from the environment or the config file, or None when it isn't set up."""
    values = {}
    try:
        for line in CONFIG.read_text().splitlines():
            key, _, value = line.strip().partition("=")
            if key and not key.startswith("#"):
                values[key] = value.strip()
    except OSError:
        pass
    url = os.environ.get("LIGHTS_CLOUD_URL", values.get("LIGHTS_CLOUD_URL"))
    token = os.environ.get("LIGHTS_DEVICE_TOKEN", values.get("LIGHTS_DEVICE_TOKEN"))
    return (url, token) if url and token else None


class Link:
    """The panel's connection to the Worker. `stream` makes the panel's live stream: a generator
    of SSE text, which counts as one viewer while it runs."""

    def __init__(self, app, stream, wake, url, token):
        self.app, self.stream, self.wake = app, stream, wake
        self.url, self.token = url, token
        self.ws = None
        self.send_lock = threading.Lock()
        self.bodies = {}
        self.watching = 0  # bumped on every change, so an old stream thread knows to stop

    def start(self):
        threading.Thread(target=self.run, daemon=True).start()

    def run(self):
        import websocket
        wait = 2
        while True:
            started = time.time()
            ws = websocket.WebSocketApp(
                self.url, header=["Authorization: Bearer " + self.token],
                on_open=self.on_open, on_message=self.on_message, on_error=self.on_error, on_close=self.on_close)
            try:
                ws.run_forever(ping_interval=PING_SECONDS, ping_timeout=10)
            except Exception:
                traceback.print_exc()
            self.ws = None
            self.watch(False)
            wait = 2 if time.time() - started > 60 else min(wait * 2, 60)
            print("cloud: reconnecting in {}s".format(wait), flush=True)
            time.sleep(wait)

    def on_open(self, ws):
        self.ws = ws
        self.bodies.clear()
        print("cloud: connected to", self.url, flush=True)

    def on_error(self, ws, error):
        print("cloud: connection error:", error, flush=True)

    def on_close(self, ws, code, reason):
        print("cloud: connection closed", code or "", reason or "", flush=True)

    def send(self, **message):
        ws = self.ws
        if ws is None:
            raise ConnectionError("not connected")
        with self.send_lock:
            ws.send(json.dumps(message))

    def on_message(self, ws, text):
        try:
            message = json.loads(text)
        except ValueError:
            print("cloud: got something that isn't JSON", flush=True)
            return
        kind = message.get("type")
        if kind == "request-body":
            self.bodies.setdefault(message["id"], []).append(base64.b64decode(message["data"]))
        elif kind == "request":
            body = b"".join(self.bodies.pop(message["id"], []))
            threading.Thread(target=self.answer, args=(message, body), daemon=True).start()
        elif kind == "watch":
            self.watch(bool(message.get("on")))

    def answer(self, request, body):
        """Run one API call through the panel and send the answer back in pieces."""
        try:
            headers = {"Content-Type": request["contentType"]} if request.get("contentType") else {}
            with self.app.test_client() as client:
                response = client.open(request["path"], method=request["method"], headers=headers, data=body)
                status, content_type, data = response.status_code, response.content_type, response.get_data()
                response.close()
        except Exception as e:
            traceback.print_exc()
            status, content_type = 500, "application/json"
            data = json.dumps({"error": "The panel failed: {}".format(e)}).encode()
        if status >= 400:
            print("cloud:", request["method"], request["path"], status, flush=True)
        try:
            self.send(type="response", id=request["id"], status=status, contentType=content_type)
            for at in range(0, len(data), CHUNK):
                self.send(type="response-body", id=request["id"], data=base64.b64encode(data[at:at + CHUNK]).decode())
            self.send(type="response-end", id=request["id"])
        except Exception as e:
            print("cloud: couldn't answer", request["path"], e, flush=True)

    def watch(self, on):
        """Start or stop sending the live stream."""
        self.watching += 1
        if on:
            threading.Thread(target=self.send_stream, args=(self.watching,), daemon=True).start()
        self.wake()  # so a stream that's waiting for news notices it should stop

    def send_stream(self, generation):
        events = self.stream()
        try:
            for text in events:
                if self.watching != generation:
                    break
                self.send(type="event", data=text)
        except Exception as e:
            print("cloud: stopped streaming:", e, flush=True)
        finally:
            events.close()


def start(app, stream, wake):
    """Connect the panel to the Worker if it's set up. Returns the Link, or None."""
    config = settings()
    if config is None:
        return None
    try:
        import websocket  # noqa: F401
    except ImportError:
        print("cloud: set up in {}, but websocket-client isn't installed "
              "(pip3 install --user websocket-client)".format(CONFIG), flush=True)
        return None
    link = Link(app, stream, wake, *config)
    link.start()
    return link
