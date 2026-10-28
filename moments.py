"""Moments: a few seconds layered over whatever the lights are playing, then gone. Frog (the
Grim Reaper) sets one off when it cackles, or when someone asks for lightning:

    {"kind": "cackle", "seconds": 3.2, "envelope": [0.1, 0.8, ...], "colors": ["#3cff00", "#a000ff"]}

`envelope` is the cackle's loudness, 30 values a second, so the house flickers with each "ha".
The show underneath keeps running and shows through as the moment fades.
"""
import random
import threading
import time

import numpy as np

import lights
from lights import NUM_PIXELS

KINDS = {
    "cackle": "the house flickers with a laugh",
    "lightning": "two or three lightning strikes",
    "pulse": "a ring of color races both ways around the house",
    "flash": "the whole house flashes one color and fades",
}
FPS = 30
x = np.arange(NUM_PIXELS)


def start(spec):
    """Layer a moment over the lights now (replacing one that's still going)."""
    kind = spec.get("kind")
    if kind not in KINDS:
        raise ValueError("a moment is one of: " + ", ".join(KINDS))
    colors = [np.array([int(c.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]) for c in spec.get("colors") or []]
    seconds = min(30.0, max(0.5, float(spec.get("seconds", DEFAULT_SECONDS[kind]))))
    layer = LAYERS[kind](colors, seconds, spec)
    began = time.time()

    def overlay(buffer):
        t = time.time() - began
        if t >= seconds:
            return None
        alpha, color = layer(t)
        base = np.asarray(buffer, dtype=float) / 255
        mixed = base * (1 - alpha[:, None]) + color * alpha[:, None]
        return (np.clip(mixed, 0, 1) * 255).astype(np.uint8).tolist()

    lights.pixels.overlay = overlay
    print(time.strftime("%H:%M:%S"), "moment:", kind, "{:.1f}s".format(seconds), flush=True)
    threading.Thread(target=keep_sending, args=(overlay,), daemon=True).start()


def keep_sending(overlay):
    """Send frames at FPS while the moment lasts, even if the show underneath draws slowly."""
    while lights.pixels.overlay is overlay:
        try:
            lights.pixels.send()
        except Exception as e:  # the show is stopping: the moment goes with it
            print("moment stopped:", e, flush=True)
            return
        time.sleep(1 / FPS)


def distance(a, b):
    return np.abs((a - b + NUM_PIXELS / 2) % NUM_PIXELS - NUM_PIXELS / 2)


def cackle(colors, seconds, spec):
    colors = colors or [np.array([0.24, 1.0, 0.0]), np.array([0.63, 0.0, 1.0])]
    envelope = np.clip(np.asarray(spec.get("envelope") or [], dtype=float), 0, 1)
    if not len(envelope):  # no recording to follow: "ha-ha-ha" at 7 a second, dying away
        t = np.arange(int(seconds * FPS)) / FPS
        envelope = np.maximum(0, np.sin(2 * np.pi * 3.5 * t)) ** 2 * np.exp(-t / seconds)
    envelope = envelope / max(0.2, envelope.max())
    sparkle = 0.55 + 0.45 * np.random.random(NUM_PIXELS)
    state = {"ha": 0, "was": 0.0}

    def layer(t):
        level = envelope[min(len(envelope) - 1, int(t * FPS))]
        if level > 0.6 and state["was"] <= 0.6:
            state["ha"] += 1  # each "ha" in the next color
            sparkle[:] = 0.55 + 0.45 * np.random.random(NUM_PIXELS)
        state["was"] = level
        return np.clip(level * 1.1, 0, 0.95) * sparkle, colors[state["ha"] % len(colors)]
    return layer


def lightning(colors, seconds, spec):
    color = colors[0] if colors else np.array([0.85, 0.85, 1.0])
    strikes = [(0.0, random.uniform(0, NUM_PIXELS), 400)]
    t = 0.0
    for _ in range(random.randint(1, 2)):
        t += random.choice((0.12, 0.2, 0.5))
        strikes.append((t, random.uniform(0, NUM_PIXELS), random.uniform(60, 180)))

    def layer(now):
        alpha = np.zeros(NUM_PIXELS)
        for at, center, width in strikes:
            if now >= at:
                alpha = np.maximum(alpha, 0.5 ** ((now - at) / 0.08) * np.exp(-(distance(x, center) / width) ** 2))
        return alpha, color
    return layer


def pulse(colors, seconds, spec):
    color = colors[0] if colors else np.array([1.0, 0.0, 0.0])
    center = random.uniform(0, NUM_PIXELS)

    def layer(t):
        front = t / seconds * NUM_PIXELS / 2
        return np.exp(-((distance(x, center) - front) / 12) ** 2) * 0.95, color
    return layer


def flash(colors, seconds, spec):
    color = colors[0] if colors else np.array([1.0, 1.0, 1.0])
    return lambda t: (np.full(NUM_PIXELS, 0.95 * (1 - t / seconds) ** 2), color)


LAYERS = {"cackle": cackle, "lightning": lightning, "pulse": pulse, "flash": flash}
DEFAULT_SECONDS = {"cackle": 3, "lightning": 1.5, "pulse": 2.5, "flash": 1.5}
