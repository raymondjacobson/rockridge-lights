"""Web control panel for the lights.

Run it on the Pi with `nohup python panel.py > panel.log 2>&1 &` and open
http://raspberrypi.local:8080 on a laptop or phone. Anything you pick plays
in the browser preview, with its sound in the browser. "Send to lights"
plays the preview's pick on the real strip (stopping any show that was
started by hand), with sound on the Bluetooth speaker. The lights keep
playing it while you preview something else.

Each of the two runs in its own process (show.py), so a stuck show can
always be stopped. It also runs on a laptop (`python3 panel.py`, needs flask
and numpy), where there's no strip and it only previews.

Once it's set up (cloud.py), the same panel is also on the internet at
https://rockridge-lights.monophonic.workers.dev, behind a password.
"""
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

from flask import Flask, Response, abort, jsonify, request, send_file
from werkzeug.utils import secure_filename

import audio
import cloud
import effects
import halloween_audio
import lights
import moments
from programs import PROGRAM, PROGRAMS

ROOT = Path(__file__).resolve().parent
STATE_FILE = ROOT / "panel_state.json"
PORT = 8080
FPS = 30
PREVIEW_IDLE_SECONDS = 120  # stop the preview this long after the last browser leaves
FROG_SECONDS = 60  # a look Frog picks stays this long, then the lights go back to what was sent
FROG_PROGRAMS = ("halloween26", "effects", "xmas25")  # the shows Frog can pick from (no sound)

DEFAULT_STATE = {
    # what's on the lights: {"program", "animation", "track"}, or None. A new Pi starts on the full show.
    "lights": {"program": "halloween_audio", "animation": None, "track": None} if lights.neopixel else None,
    "schedule": True,    # on the lights, only play between sunset and OFF_HOUR
    "brightness": lights.BRIGHTNESS,
    "volume": audio.volume,
    "latency": audio.latency["pi"],
}


def title(name):
    return name.replace("_", " ").capitalize()


def doc(function):
    return (function.__doc__ or "").strip().split("\n")[0]


def load_state():
    state = dict(DEFAULT_STATE)
    try:
        saved = json.loads(STATE_FILE.read_text())
    except (OSError, ValueError):
        return state
    if "output" in saved:  # from before the lights and the preview were separate
        if saved["output"] == "lights" and saved.get("program"):
            saved["lights"] = {k: saved.get(k) for k in ("program", "animation", "track")}
    state.update({k: saved[k] for k in DEFAULT_STATE if k in saved})
    return state


class Player:
    """One show running in a show.py process: on the lights, or the preview."""

    def __init__(self, engine, on_lights):
        self.engine = engine
        self.on_lights = on_lights
        self.lock = threading.RLock()
        self.process = None
        self.pick = None
        self.playing = self.error = self.audio = None
        self.frame = ""
        self.frame_seq = 0

    def snapshot(self):
        now = time.time()
        a = self.audio
        return {
            **(self.pick or {"program": None, "animation": None, "track": None}),
            "playing": self.playing,
            "error": self.error,
            "audio": a and {
                **a,
                "url": sound_url(a["kind"], a["track"]),
                "elapsed": now - a["started"],
            },
        }

    def play(self, pick, **settings):
        with self.lock:
            self.stop()
            self.pick = pick
            if pick is None:
                return
            args = dict(pick, lights=self.on_lights, **settings)
            self.process = subprocess.Popen(
                [sys.executable, str(ROOT / "show.py"), json.dumps(args)], cwd=str(ROOT),
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True,
                start_new_session=True)  # its own group, so its sound player is stopped with it
            threading.Thread(target=self.read, args=(self.process,), daemon=True).start()
            self.engine.bump()

    def read(self, process):
        for line in process.stdout:
            if process is not self.process:
                continue
            try:
                message = json.loads(line)
            except ValueError:
                continue
            if "frame" in message:
                with self.engine.changed:
                    self.frame = message["frame"]
                    self.frame_seq += 1
                    self.engine.changed.notify_all()
                continue
            if "playing" in message:
                self.playing = message["playing"]
            if "audio" in message:
                self.audio = message["audio"]
            if "error" in message:
                self.error = message["error"]
            self.engine.bump()
        code = process.wait()
        if process is self.process:
            self.playing = self.audio = None
            if code and not self.error:
                self.error = "the show quit unexpectedly"
            self.engine.bump()

    def tell(self, **changes):
        process = self.process
        if process:
            try:
                process.stdin.write(json.dumps(changes) + "\n")
                process.stdin.flush()
            except (BrokenPipeError, ValueError):
                pass

    def stop(self):
        with self.lock:
            process, self.process = self.process, None
            self.pick = self.playing = self.error = self.audio = None
            if process:
                end_process(process)
            self.engine.bump()


def sound_url(kind, name):
    """Where browsers get a track. It names the version, so a copy kept elsewhere (the Worker's)
    is replaced when the file changes."""
    try:
        version = int((audio.CACHE / "{}-{}.mp3".format(kind, name)).stat().st_mtime)
    except OSError:
        version = 0
    return "/sounds/{}/{}.mp3?v={}".format(kind, name, version)


def end_process(process):
    """Stop a show.py process (it turns its lights off as it goes) and anything it started."""
    process.terminate()
    try:
        process.wait(5)
    except subprocess.TimeoutExpired:
        print("show didn't stop within 5 seconds; killing it", flush=True)
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    process.wait()


class Engine:
    """The lights and the preview, and keeping the browsers up to date."""

    def __init__(self):
        self.changed = threading.Condition()
        self.state = load_state()
        self.version = 0
        self.viewers = 0
        self.last_viewer = time.time()
        self.other_shows = []
        self.speaker = None
        self.lights = Player(self, on_lights=True)
        self.preview = Player(self, on_lights=False)
        self.frog = None  # a look Frog put on the lights for now: {"pick", "until"}
        self.frog_timer = None

    def bump(self):
        with self.changed:
            self.version += 1
            self.changed.notify_all()

    def snapshot(self):
        today = lights.datetime.now().astimezone().date()
        return {
            **{k: self.state[k] for k in ("schedule", "brightness", "volume", "latency")},
            "lights": self.lights.snapshot(),
            "preview": self.preview.snapshot(),
            "has_leds": lights.neopixel is not None,
            "other_shows": [name for _, name in self.other_shows],
            "speaker": self.speaker,
            "show_time": lights.is_show_time(),
            "frog": self.frog and {"seconds_left": max(0, self.frog["until"] - time.time())},
            "window": [lights.show_start(today).strftime("%-I:%M %p"),
                       lights.show_end(today).strftime("%-I:%M %p")],
        }

    def save(self):
        STATE_FILE.write_text(json.dumps(self.state, indent=2))

    def play(self, where, pick):
        if where == "lights":
            if pick and lights.neopixel is None:
                raise ValueError("There's no LED strip on this machine")
            self.state["lights"] = pick
            self.save()
            self.start_lights()
        else:
            self.preview.play(pick)

    def start_lights(self, pick=None):
        """Play `pick` on the lights for now, or else what was last sent to them."""
        if pick is None:
            pick = self.state["lights"]
            self.end_frog_look()
        with self.lights.lock:
            self.lights.stop()
            if pick:
                for pid, name in find_other_shows():
                    print("stopping", name, pid, flush=True)
                    stop_process(pid)
            self.lights.play(pick, schedule=self.state["schedule"],
                             brightness=self.state["brightness"], latency=self.state["latency"])

    # Frog (the Grim Reaper next door, through the Worker) can put a look on the lights for a
    # minute and set off moments, but only while they're on: they keep their own schedule.

    def frog_refusal(self):
        """Why Frog can't change the lights right now, or None if it can."""
        if lights.neopixel is None:
            return "there are no lights on this computer"
        if not self.state["lights"] or self.lights.process is None:
            return "the lights are off"
        if self.state["schedule"] and not lights.is_show_time():
            return "the lights are asleep until {}".format(lights.next_show_start().strftime("%-I:%M %p"))
        return None

    def frog_look(self, body):
        refusal = self.frog_refusal()
        if refusal:
            raise Refused(refusal)
        if body.get("effect"):
            pick = {"program": "effects", "animation": None, "track": None, "effect": effects.check(body["effect"])}
        else:
            program, animation = body.get("program"), body.get("animation")
            if program not in FROG_PROGRAMS or animation not in {a.__name__ for a in PROGRAM[program]["animations"]}:
                raise ValueError("no animation {}/{}".format(program, animation))
            pick = {"program": program, "animation": animation, "track": None}
        seconds = min(600.0, max(10.0, float(body.get("seconds", FROG_SECONDS))))
        with self.lights.lock:
            self.start_lights(pick)
            self.end_frog_look()
            look = self.frog = {"pick": pick, "until": time.time() + seconds}
            self.frog_timer = threading.Timer(seconds, self.frog_look_over, args=(look,))
            self.frog_timer.daemon = True
            self.frog_timer.start()
        print("frog: {} for {:.0f}s".format(pick.get("effect") or pick["animation"], seconds), flush=True)
        self.bump()
        return {"seconds": seconds}

    def frog_look_over(self, look):
        with self.lights.lock:
            if self.frog is look:
                print("frog: look over, back to", (self.state["lights"] or {}).get("program"), flush=True)
                self.start_lights()

    def end_frog_look(self):
        if self.frog_timer:
            self.frog_timer.cancel()
        self.frog = self.frog_timer = None

    def frog_back(self):
        """Back to what was sent to the lights, now."""
        with self.lights.lock:
            was = self.frog is not None
            if was:
                self.start_lights()
        return was

    def frog_moment(self, spec):
        refusal = self.frog_refusal()
        if refusal:
            raise Refused(refusal)
        if not isinstance(spec, dict) or spec.get("kind") not in moments.KINDS:
            raise ValueError("a moment is one of: " + ", ".join(moments.KINDS))
        for c in spec.get("colors") or []:
            effects.color(c)
        self.lights.tell(moment=spec)

    def frog_status(self):
        lights_pick = self.lights.snapshot()
        program = PROGRAM.get(lights_pick["program"] or "")
        catalog = [{"program": p, "animation": a.__name__, "about": doc(a)}
                   for p in FROG_PROGRAMS for a in PROGRAM[p]["animations"]]
        return {
            "refusal": self.frog_refusal(),
            "playing": program and {"show": program["name"], "animation": lights_pick["playing"],
                                    "effect": lights_pick.get("effect")},
            "frog_look": self.frog and {"seconds_left": round(self.frog["until"] - time.time())},
            "catalog": catalog, "effects": effects.KINDS, "moments": moments.KINDS,
        }

    def settings(self, changes):
        if "brightness" in changes:
            self.state["brightness"] = min(1.0, max(0.02, float(changes["brightness"])))
            self.lights.tell(brightness=self.state["brightness"])
        if "volume" in changes:
            self.state["volume"] = int(changes["volume"])
            audio.set_volume(self.state["volume"])
        if "latency" in changes:
            self.state["latency"] = float(changes["latency"])
            self.lights.tell(latency=self.state["latency"])
        if "schedule" in changes and bool(changes["schedule"]) != self.state["schedule"]:
            self.state["schedule"] = bool(changes["schedule"])
            if self.state["lights"]:
                self.start_lights()
        self.save()
        self.bump()

    def start(self):
        audio.volume = self.state["volume"]
        if self.state["lights"] and lights.neopixel is not None:
            self.start_lights()
        threading.Thread(target=self.watch_system, daemon=True).start()
        threading.Thread(target=prepare_tracks, daemon=True).start()

    def watch_system(self):
        """Every so often, note other shows and the speaker, reconnect the speaker if it's
        dropped, and stop the preview once nobody's watching it."""
        tries = 0
        while True:
            others = find_other_shows()
            speaker = audio._bluetooth_sink()
            if speaker is None and self.lights.audio is not None and tries % 6 == 0:
                reconnect_speaker()
            tries += 1
            if others != self.other_shows or speaker != self.speaker:
                self.other_shows, self.speaker = others, speaker
                self.bump()
            if self.viewers:
                self.last_viewer = time.time()
            elif self.preview.process and time.time() - self.last_viewer > PREVIEW_IDLE_SECONDS:
                self.preview.stop()
            time.sleep(10)


def find_other_shows():
    """(pid, script) for python scripts from this repo running in processes the panel didn't start."""
    shows = []
    if not os.path.isdir("/proc"):
        return shows
    ours = {os.getpid()} | {p.process.pid for p in (engine.lights, engine.preview) if p.process}
    for pid in os.listdir("/proc"):
        if not pid.isdigit() or int(pid) in ours:
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


class Refused(Exception):
    """Frog asked for something the lights won't do now (they're off or asleep)."""


@app.errorhandler(ValueError)
def bad_request(e):
    return jsonify(error=str(e)), 400


@app.errorhandler(Refused)
def refused(e):
    return jsonify(error=str(e), refused=True), 409


@app.route("/")
def index():
    return send_file(str(ROOT / "web" / "index.html"))


def live_events():
    """The live stream as SSE text: the state whenever it changes, and both players' frames.
    Each browser on /api/stream gets one, and so does the Worker while anyone watches there."""
    engine.viewers += 1
    players = {"lights": engine.lights, "preview": engine.preview}
    sent = {where: -1 for where in players}
    sent_version = -1
    try:
        while True:
            with engine.changed:
                engine.changed.wait_for(lambda: engine.version != sent_version or any(
                    p.frame_seq != sent[w] for w, p in players.items()), timeout=10)
                version = engine.version
                frames = {w: (p.frame_seq, p.frame) for w, p in players.items() if p.frame_seq != sent[w]}
            if version != sent_version:
                sent_version = version
                yield "event: state\ndata: {}\n\n".format(json.dumps(engine.snapshot()))
            for where, (seq, frame) in frames.items():
                sent[where] = seq
                if frame:
                    yield "event: {}\ndata: {}\n\n".format(where, frame)
            if frames:
                time.sleep(1 / FPS)
            else:
                yield ": still here\n\n"
    finally:
        engine.viewers -= 1


@app.route("/api/stream")
def stream():
    return Response(live_events(), mimetype="text/event-stream",
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


def where_from(body):
    where = body.get("where", "preview")
    if where not in ("preview", "lights"):
        raise ValueError("play on the preview or the lights")
    return where


@app.route("/api/play", methods=["POST"])
def play():
    body = request.get_json(force=True)
    if body.get("program") not in PROGRAM:
        raise ValueError("unknown program")
    pick = {"program": body["program"], "animation": body.get("animation"), "track": body.get("track")}
    engine.play(where_from(body), pick)
    return jsonify(ok=True)


@app.route("/api/stop", methods=["POST"])
def stop():
    engine.play(where_from(request.get_json(force=True)), None)
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


@app.route("/api/frog")
def frog_status():
    return jsonify(engine.frog_status())


@app.route("/api/frog/look", methods=["POST"])
def frog_look():
    return jsonify(ok=True, **engine.frog_look(request.get_json(force=True)))


@app.route("/api/frog/moment", methods=["POST"])
def frog_moment():
    engine.frog_moment(request.get_json(force=True))
    return jsonify(ok=True)


@app.route("/api/frog/back", methods=["POST"])
def frog_back():
    return jsonify(ok=True, was_frogs=engine.frog_back())


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
    engine.preview.stop()
    engine.lights.stop()


if __name__ == "__main__":
    engine.start()
    cloud.start(app, live_events, engine.bump)
    try:
        app.run(host="0.0.0.0", port=PORT, threaded=True)
    finally:
        shutdown()
