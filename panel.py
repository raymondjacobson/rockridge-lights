"""Web control panel for the lights.

Run it on the Pi with `nohup python panel.py > panel.log 2>&1 &` and open
http://raspberrypi.local:8080 on a laptop or phone. Pick any show to watch it
in the browser; "Send to lights" plays it on the real strip instead (stopping
any show that was started by hand), with sound on the Bluetooth speaker.

It also runs on a laptop (`python3 panel.py`, needs flask and numpy), where
there's no strip and it only previews.
"""
import base64
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
import traceback
from pathlib import Path

import numpy as np
from flask import Flask, Response, abort, jsonify, request, send_file
from werkzeug.utils import secure_filename

import audio
import halloween26
import halloween_audio
import lights
import test_white
import xmas25

ROOT = Path(__file__).resolve().parent
STATE_FILE = ROOT / "panel_state.json"
PORT = 8080
FPS = 30

PROGRAMS = [
    {"id": "halloween_audio", "name": "Halloween with sound", "seconds": 1, "shuffle": False,
     "play_all": [halloween_audio.halloween_night],
     "animations": halloween_audio.SOUNDSCAPES + halloween_audio.VISUALIZERS},
    {"id": "halloween26", "name": "Halloween reds", "seconds": halloween26.PATTERN_SECONDS,
     "play_all": halloween26.PATTERNS, "animations": halloween26.PATTERNS + [halloween26.red_sweep]},
    {"id": "xmas25", "name": "Christmas 2025", "seconds": 30, "animations": xmas25.ANIMATIONS},
    {"id": "tests", "name": "Tests", "seconds": 30, "animations": [test_white.white_circle]},
]
PROGRAM = {p["id"]: p for p in PROGRAMS}

DEFAULT_STATE = {
    "program": None,     # what to play: a program id,
    "animation": None,   # optionally one animation in it,
    "track": None,       # and for sound shows, optionally one track
    "output": "preview",  # or "lights"
    "schedule": True,    # on the lights, only play between sunset and OFF_HOUR
    "brightness": lights.BRIGHTNESS,
    "volume": audio.volume,
    "latency": audio.latency["pi"],
}


def title(name):
    return name.replace("_", " ").capitalize()


def doc(function):
    return (function.__doc__ or "").strip().split("\n")[0]


class Engine:
    """Runs the chosen show in a background thread and keeps the browsers up to date."""

    def __init__(self):
        self.lock = threading.RLock()
        self.changed = threading.Condition()
        self.thread = None
        self.state = dict(DEFAULT_STATE)
        try:
            self.state.update(json.loads(STATE_FILE.read_text()))
        except (OSError, ValueError):
            pass
        self.version = 0
        self.frame = ""
        self.frame_seq = 0
        self.viewers = 0
        self.playing = None
        self.error = None
        self.other_shows = []
        self.speaker = None
        lights.pixels.listeners.append(self.on_frame)
        audio.listeners.append(lambda playback: self.bump())

    # Browsers

    def bump(self):
        with self.changed:
            self.version += 1
            self.changed.notify_all()

    def on_frame(self, buffer):
        if not self.viewers:
            return
        rgb = np.clip(np.asarray(buffer, dtype=float), 0, 255).astype(np.uint8)
        with self.changed:
            self.frame = base64.b64encode(rgb.tobytes()).decode()
            self.frame_seq += 1
            self.changed.notify_all()

    def snapshot(self):
        playback = audio.current
        now = time.time()
        today = lights.datetime.now().astimezone().date()
        return {
            **self.state,
            "playing": self.playing,
            "error": self.error,
            "has_leds": lights.neopixel is not None,
            "other_shows": [name for _, name in self.other_shows],
            "speaker": self.speaker,
            "show_time": lights.is_show_time(),
            "window": [lights.show_start(today).strftime("%-I:%M %p"),
                       lights.show_end(today).strftime("%-I:%M %p")],
            "audio": playback and {
                "track": playback.track.name,
                "title": playback.track.title,
                "url": "/sounds/{}/{}.mp3".format(playback.track.kind, playback.track.name),
                "elapsed": now - playback.started,
                "duration": playback.track.duration,
                "output": playback.output,
            },
        }

    # Playing

    def save(self):
        STATE_FILE.write_text(json.dumps(self.state, indent=2))

    def play(self, program=None, animation=None, track=None):
        with self.lock:
            self.state.update(program=program, animation=animation, track=track)
            self.save()
            self.restart()

    def restart(self):
        with self.lock:
            self.stop_thread()
            self.error = None
            program = PROGRAM.get(self.state["program"])
            if program is None:
                lights.clear()
                self.playing = None
                self.bump()
                return
            animations = program.get("play_all", program["animations"])
            name = self.state["animation"]
            if name:
                animations = [a for a in program["animations"] if a.__name__ == name][:1]
            track = self.state["track"] and self.find_track(self.state["track"])
            if track:
                animations = [self.play_track(track, animations[0] if name else None)]
            if not animations:
                return
            scheduled = self.state["schedule"] and self.state["output"] == "lights"
            lights.pixels.interrupt.clear()
            self.thread = threading.Thread(
                target=self.run, daemon=True,
                args=([self.watch(a) for a in animations], program["seconds"],
                      program.get("shuffle", True), scheduled))
            self.thread.start()

    def find_track(self, name):
        try:
            return audio.find(name)
        except KeyError:
            return None

    def play_track(self, track, visual=None):
        if visual is None:
            visual = halloween_audio.scene_for(track) if track.kind == "ambience" else halloween_audio.dance_of_the_dead

        def animation():
            visual(track)
        animation.__name__ = visual.__name__
        return animation

    def watch(self, animation):
        def watched():
            if self.playing != animation.__name__:
                self.playing = animation.__name__
                self.bump()
            animation()
        watched.__name__ = animation.__name__
        return watched

    def run(self, animations, seconds, shuffle, scheduled):
        try:
            lights.rotate(animations, seconds=seconds, shuffle=shuffle, scheduled=scheduled)
        except lights.Stopped:
            pass
        except Exception as e:
            traceback.print_exc()
            self.error = "{}: {}".format(type(e).__name__, e)
            self.playing = None
            self.bump()

    def stop_thread(self):
        if self.thread and self.thread.is_alive():
            lights.pixels.interrupt.set()
            self.thread.join(10)
            if self.thread.is_alive():
                # Usually it's stuck inside the LED library, which Python can't
                # interrupt, and it keeps the strip. Keep it off the strip if it
                # wakes, and start the panel over so the strip is really let go.
                print("show didn't stop within 10 seconds; restarting the panel", flush=True)
                lights.pixels.retired.add(self.thread)
                threading.Timer(3, restart_panel).start()
        self.thread = None

    # Settings

    def settings(self, changes):
        if changes.get("output") == "lights" and lights.neopixel is None:
            raise ValueError("There's no LED strip on this machine")
        with self.lock:
            if "brightness" in changes:
                lights.pixels.brightness = self.state["brightness"] = min(1.0, max(0.02, float(changes["brightness"])))
            if "volume" in changes:
                self.state["volume"] = int(changes["volume"])
                audio.set_volume(self.state["volume"])
            if "latency" in changes:
                audio.latency["pi"] = self.state["latency"] = float(changes["latency"])
            restart = False
            if "schedule" in changes and bool(changes["schedule"]) != self.state["schedule"]:
                self.state["schedule"] = bool(changes["schedule"])
                restart = self.state["output"] == "lights"
            if "output" in changes and changes["output"] != self.state["output"]:
                self.stop_thread()
                self.set_output(changes["output"])
                restart = True
            self.save()
            if restart:
                self.restart()
            self.bump()

    def set_output(self, output):
        if output == "lights":
            for pid, name in find_other_shows():
                print("stopping", name, pid, flush=True)
                stop_process(pid)
            lights.pixels.to_leds = True
            audio.output = "pi"
        else:
            lights.pixels.to_leds = False
            lights.pixels.release_leds()
            audio.output = "browser"
        self.state["output"] = output

    def start(self):
        lights.pixels.brightness = self.state["brightness"]
        audio.latency["pi"] = self.state["latency"]
        audio.volume = self.state["volume"]
        output = self.state["output"]
        if output == "lights" and lights.neopixel is None:
            output = "preview"
        self.set_output(output)
        self.restart()
        threading.Thread(target=self.watch_system, daemon=True).start()
        threading.Thread(target=prepare_tracks, daemon=True).start()

    def watch_system(self):
        """Every so often, note other shows and the speaker, and reconnect the speaker if it's dropped."""
        tries = 0
        while True:
            others = find_other_shows()
            speaker = audio._bluetooth_sink()
            if speaker is None and self.state["output"] == "lights" and tries % 6 == 0:
                reconnect_speaker()
            tries += 1
            if others != self.other_shows or speaker != self.speaker:
                self.other_shows, self.speaker = others, speaker
                self.bump()
            time.sleep(10)


def find_other_shows():
    """(pid, script) for python scripts from this repo running in other processes."""
    shows = []
    if not os.path.isdir("/proc"):
        return shows
    for pid in os.listdir("/proc"):
        if not pid.isdigit() or int(pid) == os.getpid():
            continue
        try:
            args = Path("/proc", pid, "cmdline").read_bytes().decode(errors="replace").split("\0")
        except OSError:
            continue
        try:
            cwd = os.readlink("/proc/{}/cwd".format(pid))
        except OSError:  # hidden for processes with extra privileges (the LED library's)
            cwd = str(ROOT)
        if len(args) > 1 and "python" in os.path.basename(args[0]) and args[1].endswith(".py"):
            script = Path(cwd, args[1]).resolve()
            if ROOT in script.parents and script.name != "panel.py":
                shows.append((int(pid), script.name))
    return shows


def stop_process(pid):
    """Stop a show and wait until it has let go of the strip."""
    try:
        for sig in (signal.SIGTERM, signal.SIGKILL):
            os.kill(pid, sig)
            for _ in range(50):
                os.kill(pid, 0)
                time.sleep(0.1)
    except ProcessLookupError:
        pass


def restart_panel():
    """Start this process over from saved state."""
    engine.save()
    os.execv(sys.executable, [sys.executable] + sys.argv)


def prepare_tracks():
    """Analyze every track ahead of time so nothing waits when it's first played."""
    for track in audio.library():
        try:
            track.features
            track.browser_file
        except Exception:
            traceback.print_exc()


# Bluetooth


def bluetoothctl(*args, timeout=20):
    try:
        return subprocess.run(["bluetoothctl"] + list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              universal_newlines=True, timeout=timeout).stdout
    except (OSError, subprocess.TimeoutExpired) as e:
        return str(e)


def bluetooth_devices():
    devices = []
    for address, name in re.findall(r"^Device (\S+) (.*)$", bluetoothctl("devices"), re.M):
        info = bluetoothctl("info", address)
        devices.append({
            "address": address,
            "name": name,
            "paired": "Paired: yes" in info,
            "connected": "Connected: yes" in info,
            "audio": "Audio Sink" in info or "Icon: audio" in info,
        })
    return devices


def reconnect_speaker():
    for device in bluetooth_devices():
        if device["paired"] and device["audio"] and not device["connected"]:
            bluetoothctl("connect", device["address"], timeout=15)


def connect_speaker(address):
    if "Paired: yes" not in bluetoothctl("info", address):
        bluetoothctl("pair", address, timeout=30)
    bluetoothctl("trust", address)
    log = bluetoothctl("connect", address, timeout=20)
    for _ in range(20):  # PulseAudio adds the speaker a moment after it connects
        sink = audio._bluetooth_sink()
        if sink:
            subprocess.run(["pactl", "set-default-sink", sink], env=audio.pulse_env())
            audio.set_volume(engine.state["volume"])
            break
        time.sleep(0.5)
    return log


# Web

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 300 * 1024 * 1024
engine = Engine()


@app.errorhandler(ValueError)
def bad_request(e):
    return jsonify(error=str(e)), 400


@app.route("/")
def index():
    return send_file(str(ROOT / "web" / "index.html"))


@app.route("/api/stream")
def stream():
    def events():
        engine.viewers += 1
        sent_seq = sent_version = -1
        last_frame = 0
        try:
            while True:
                with engine.changed:
                    engine.changed.wait_for(
                        lambda: engine.frame_seq != sent_seq or engine.version != sent_version, timeout=10)
                    seq, version, frame = engine.frame_seq, engine.version, engine.frame
                if version != sent_version:
                    sent_version = version
                    yield "event: state\ndata: {}\n\n".format(json.dumps(engine.snapshot()))
                if seq != sent_seq and frame:
                    time.sleep(max(0, last_frame + 1 / FPS - time.time()))
                    sent_seq, last_frame = seq, time.time()
                    yield "event: frame\ndata: {}\n\n".format(frame)
                elif seq == sent_seq:
                    yield ": still here\n\n"
        finally:
            engine.viewers -= 1

    return Response(events(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/library")
def library():
    tracks = {kind: [] for kind in audio.KINDS}
    for track in audio.library():
        cached = any(audio.CACHE.glob("{}-{}-*.npz".format(track.kind, track.name)))
        tracks[track.kind].append({
            "name": track.name, "title": track.title,
            "duration": track.duration if cached else None,
            "scene": halloween_audio.scene_for(track).__name__ if track.kind == "ambience" else None,
        })
    credits = audio.SOUNDS / "credits.json"
    return jsonify(
        programs=[{"id": p["id"], "name": p["name"],
                   "animations": [{"name": a.__name__, "title": title(a.__name__), "doc": doc(a)}
                                  for a in p["animations"]]} for p in PROGRAMS],
        visualizers=[a.__name__ for a in halloween_audio.VISUALIZERS],
        tracks=tracks,
        credits=json.loads(credits.read_text()) if credits.exists() else [],
    )


@app.route("/api/play", methods=["POST"])
def play():
    body = request.get_json(force=True)
    if body.get("program") not in PROGRAM:
        raise ValueError("unknown program")
    engine.play(body["program"], body.get("animation"), body.get("track"))
    return jsonify(ok=True)


@app.route("/api/stop", methods=["POST"])
def stop():
    engine.play(None)
    return jsonify(ok=True)


@app.route("/api/settings", methods=["POST"])
def settings():
    engine.settings(request.get_json(force=True))
    return jsonify(ok=True)


@app.route("/sounds/<kind>/<name>.mp3")
def sound(kind, name):
    try:
        track = audio.find(name)
    except KeyError:
        abort(404)
    return send_file(str(track.browser_file), mimetype="audio/mpeg", conditional=True)


@app.route("/api/upload", methods=["POST"])
def upload():
    kind = request.form.get("kind", "music")
    file = request.files.get("file")
    if kind not in audio.KINDS or file is None:
        raise ValueError("send a file and a kind (music or ambience)")
    name = secure_filename(file.filename).lower()
    if Path(name).suffix not in audio.EXTENSIONS:
        raise ValueError("unsupported audio type")
    folder = audio.SOUNDS / kind
    folder.mkdir(parents=True, exist_ok=True)
    file.save(str(folder / name))
    threading.Thread(target=prepare_tracks, daemon=True).start()
    return jsonify(ok=True, name=Path(name).stem)


@app.route("/api/bluetooth")
def bluetooth():
    return jsonify(devices=bluetooth_devices(), speaker=audio._bluetooth_sink())


@app.route("/api/bluetooth/scan", methods=["POST"])
def bluetooth_scan():
    bluetoothctl("--timeout", "12", "scan", "on", timeout=20)
    return jsonify(devices=bluetooth_devices(), speaker=audio._bluetooth_sink())


@app.route("/api/bluetooth/connect", methods=["POST"])
def bluetooth_connect():
    log = connect_speaker(request.get_json(force=True)["address"])
    return jsonify(log=log, devices=bluetooth_devices(), speaker=audio._bluetooth_sink())


@app.route("/api/bluetooth/disconnect", methods=["POST"])
def bluetooth_disconnect():
    bluetoothctl("disconnect", request.get_json(force=True)["address"])
    return jsonify(devices=bluetooth_devices(), speaker=audio._bluetooth_sink())


def shutdown():
    engine.stop_thread()
    if lights.pixels.to_leds:
        lights.pixels.release_leds()


if __name__ == "__main__":
    engine.start()
    try:
        app.run(host="0.0.0.0", port=PORT, threaded=True)
    finally:
        shutdown()
