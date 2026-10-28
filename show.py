"""Plays one pick from programs.py in its own process, for the control panel.

    python show.py '{"program": "halloween26", "lights": true, "schedule": true}'

With "lights" it drives the real strip and plays sound on the Pi's speaker;
otherwise it only previews, leaving the sound to the browser. It reports
what it's doing on stdout as JSON lines (frames, the animation playing, the
track) and takes setting changes ({"brightness": 0.5}, {"latency": 0.3}) on
stdin, and moments to layer over the show ({"moment": {"kind": "lightning"}},
see moments.py). It stops when it's killed or when the panel goes away.
"""
import base64
import json
import os
import signal
import sys
import threading
import time
import traceback

import audio
import lights
import moments
import programs

FPS = 30


def main():
    pick = json.loads(sys.argv[1])
    out = os.fdopen(os.dup(1), "w", buffering=1)
    os.dup2(2, 1)  # anything the shows print goes to the panel's log
    out_lock = threading.Lock()

    def report(**message):
        with out_lock:
            out.write(json.dumps(message) + "\n")

    on_lights = bool(pick.get("lights"))
    lights.pixels.to_leds = on_lights
    lights.pixels.brightness = pick.get("brightness", lights.BRIGHTNESS)
    audio.output = "pi" if on_lights else "browser"
    audio.latency["pi"] = pick.get("latency", audio.latency["pi"])

    last_frame = [0.0]

    def on_frame(buffer):
        now = time.time()
        if now - last_frame[0] >= 1 / FPS:
            last_frame[0] = now
            data = bytes(min(255, max(0, int(c))) for color in buffer for c in color)
            report(frame=base64.b64encode(data).decode())
    lights.pixels.listeners.append(on_frame)

    def on_audio(playback):
        report(audio=playback and {
            "track": playback.track.name, "kind": playback.track.kind, "title": playback.track.title,
            "started": playback.started, "duration": playback.track.duration, "output": playback.output,
        })
    audio.listeners.append(on_audio)

    def listen():
        for line in sys.stdin:
            changes = json.loads(line)
            if "brightness" in changes:
                lights.pixels.brightness = float(changes["brightness"])
            if "latency" in changes:
                audio.latency["pi"] = float(changes["latency"])
            if "moment" in changes:
                try:
                    moments.start(changes["moment"])
                except (ValueError, TypeError) as e:
                    print("couldn't play moment", changes["moment"], e, flush=True)
        os.kill(os.getpid(), signal.SIGTERM)  # the panel is gone
    threading.Thread(target=listen, daemon=True).start()

    def announced(animation):
        def run():
            report(playing=animation.__name__)
            animation()
        run.__name__ = animation.__name__
        return run

    try:
        animations, seconds, shuffle = programs.build(pick["program"], pick.get("animation"), pick.get("track"),
                                                           pick.get("effect"))
        lights.rotate([announced(a) for a in animations], seconds=seconds, shuffle=shuffle,
                      scheduled=on_lights and pick.get("schedule", True))
    except Exception as e:
        traceback.print_exc()
        report(error="{}: {}".format(type(e).__name__, e))
        sys.exit(1)


if __name__ == "__main__":
    main()
