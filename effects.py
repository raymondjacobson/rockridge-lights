"""Looks made to order: an effect, its colors and its speed. Frog (the Grim Reaper) picks these
when someone asks for something like "make the lights red and drip like blood":

    {"kind": "drips", "colors": ["#ff0000"], "speed": 1}

KINDS lists the effects. A few ready-made ones (PRESETS) are also a show in the control panel.
"""
import random

import numpy as np

from halloween26 import distance, frames, show, tint, x
from lights import NUM_PIXELS

KINDS = {
    "solid": "steady color; with several colors, long blocks of each",
    "breathe": "the whole house slowly swells and dims",
    "chase": "bands of color run around the house",
    "waves": "colors flow into each other in slow waves, like a lava lamp",
    "drips": "drops slide along and leave a fading stain, like blood",
    "twinkle": "a dim glow with lights sparkling here and there",
    "flicker": "every light flickers on its own, like fire or candles",
    "lightning": "dark, with sudden strikes of the second color (or white)",
}
SECONDS = 60  # how long each call runs; rotate() calls it again


def color(text):
    """'#rrggbb' as (R, G, B) in 0..1."""
    text = str(text).strip().lstrip("#")
    if len(text) != 6:
        raise ValueError("colors are #rrggbb, not {!r}".format(text))
    return np.array([int(text[i:i + 2], 16) / 255 for i in (0, 2, 4)])


def check(spec):
    """A clean copy of an effect spec, or ValueError saying what's wrong."""
    if not isinstance(spec, dict) or spec.get("kind") not in KINDS:
        raise ValueError("an effect needs a kind: " + ", ".join(KINDS))
    colors = spec.get("colors") or ["#ff0000"]
    if not isinstance(colors, list) or not 1 <= len(colors) <= 4:
        raise ValueError("an effect takes 1 to 4 colors")
    for c in colors:
        color(c)
    try:
        speed = float(spec.get("speed", 1))
    except (TypeError, ValueError):
        raise ValueError("speed is a number, 1 is normal")
    return {"kind": spec["kind"], "colors": ["#" + str(c).strip().lstrip("#").lower() for c in colors],
            "speed": min(3.0, max(0.25, speed))}


def animation(spec, name=None, doc=None):
    """An animation for rotate() that plays this effect. It keeps its state between calls."""
    spec = check(spec)
    colors = np.array([color(c) for c in spec["colors"]])
    draw = DRAW[spec["kind"]](colors, spec["speed"])
    started = []

    def run():
        for t, dt, fade in frames(SECONDS):
            # fade in once at the start, but don't dip every minute after that
            fade = 1.0 if started else fade if t < SECONDS / 2 else 1.0
            show(draw(t, dt), fade)
        started.append(True)
    run.__name__ = name or spec["kind"]
    run.__doc__ = doc or KINDS[spec["kind"]].capitalize() + "."
    return run


def blend(colors, amount):
    """Mix along the colors: amount 0 is the first, 1 the last, per light."""
    if len(colors) == 1:
        return np.tile(colors[0], (len(amount), 1))
    position = np.clip(amount, 0, 1) * (len(colors) - 1)
    low = np.floor(position).astype(int).clip(0, len(colors) - 2)
    mix = (position - low)[:, None]
    return colors[low] * (1 - mix) + colors[low + 1] * mix


def blocks(colors, length):
    """Which color each light gets, in blocks of `length` lights."""
    return colors[(x // length) % len(colors)]


def solid(colors, speed):
    base = blocks(colors, NUM_PIXELS // len(colors) // 2 or 1)
    return lambda t, dt: base


def breathe(colors, speed):
    base = blocks(colors, 50)
    return lambda t, dt: base * (0.2 + 0.8 * (0.5 - 0.5 * np.cos(2 * np.pi * t * speed / 5)))


def chase(colors, speed):
    def draw(t, dt):
        shifted = (x - t * 25 * speed) % NUM_PIXELS
        band = (shifted // 40).astype(int)
        lit = np.where(shifted % 40 < 16, 1.0, 0.04)
        return colors[band % len(colors)] * lit[:, None]
    return draw


def waves(colors, speed):
    palette = colors if len(colors) > 1 else np.array([colors[0] * 0.25, colors[0]])

    def draw(t, dt):
        s = t * speed
        amount = 0.5 + 0.25 * np.sin(x / 37 + s * 0.6) + 0.25 * np.sin(x / 23 - s * 0.45)
        glow = 0.45 + 0.55 * (0.5 + 0.5 * np.sin(x / 61 - s * 0.3))
        return blend(palette, amount) * glow[:, None]
    return draw


def drips(colors, speed):
    stain = np.zeros(NUM_PIXELS)
    drops = []  # [position, direction, speed, distance left]
    base = colors[-1] if len(colors) > 1 else colors[0]

    def draw(t, dt):
        if len(drops) < 12 and random.random() < dt * 1.2 * speed:
            drops.append([random.uniform(0, NUM_PIXELS), random.choice((-1, 1)),
                          random.uniform(1, 3) * speed, random.uniform(30, 80)])
        stain[:] *= 0.5 ** (dt / 4)
        bright = np.zeros(NUM_PIXELS)
        for drop in drops:
            drop[2] += 1.5 * dt * speed
            step = drop[2] * dt
            drop[0] = (drop[0] + drop[1] * step) % NUM_PIXELS
            drop[3] -= step
            stain[int(drop[0])] = max(stain[int(drop[0])], 0.45)
            bright += np.exp(-(distance(x, drop[0]) / 1.2) ** 2)
        drops[:] = [d for d in drops if d[3] > 0]
        return tint(0.04 + stain, base) + tint(bright * 0.8, colors[0])
    return draw


def twinkle(colors, speed):
    sparkle = np.zeros(NUM_PIXELS)
    hue = np.zeros(NUM_PIXELS, dtype=int)

    def draw(t, dt):
        sparkle[:] *= 0.5 ** (dt * 2 * speed)
        new = np.random.random(NUM_PIXELS) < dt * 0.6 * speed
        sparkle[new] = 1.0
        hue[new] = np.random.randint(0, len(colors), new.sum())
        return colors[0] * 0.06 + colors[hue] * sparkle[:, None]
    return draw


def flicker(colors, speed):
    level = np.random.random(NUM_PIXELS)
    palette = colors if len(colors) > 1 else np.array([colors[0] * 0.35, colors[0]])

    def draw(t, dt):
        target = np.random.random(NUM_PIXELS)
        level[:] += (target - level) * min(1.0, dt * 8 * speed)
        return blend(palette, level) * (0.35 + 0.65 * level)[:, None]
    return draw


def lightning(colors, speed):
    strike_color = colors[1] if len(colors) > 1 else np.array([0.85, 0.85, 1.0])
    flash = np.zeros(NUM_PIXELS)
    next_strike = [random.uniform(1, 3)]

    def draw(t, dt):
        flash[:] *= 0.5 ** (dt / 0.07)
        if t >= next_strike[0]:
            center, width = random.uniform(0, NUM_PIXELS), random.uniform(40, 160)
            flash[:] = np.maximum(flash, np.exp(-(distance(x, center) / width) ** 2))
            next_strike[0] = t + random.choice((0.12, 0.25, random.uniform(2, 7) / speed))
        return colors[0] * 0.08 + strike_color * flash[:, None]
    return draw


DRAW = {"solid": solid, "breathe": breathe, "chase": chase, "waves": waves, "drips": drips,
        "twinkle": twinkle, "flicker": flicker, "lightning": lightning}

PRESETS = [
    animation({"kind": "drips", "colors": ["#ff0000", "#550000"]}, "blood", "Red drops slide along and leave a stain."),
    animation({"kind": "twinkle", "colors": ["#3cff00", "#a000ff"]}, "toxic_twinkle", "Dim green with green and purple sparkles."),
    animation({"kind": "chase", "colors": ["#ff4d00", "#8000ff"]}, "orange_purple_chase", "Orange and purple bands run around the house."),
    animation({"kind": "flicker", "colors": ["#ff1a00", "#ff8a00"]}, "hellfire", "Every light flickers like fire."),
    animation({"kind": "waves", "colors": ["#2a0055", "#8000ff", "#00ff60"]}, "ghostly_waves", "Purple and green flowing slowly."),
    animation({"kind": "lightning", "colors": ["#1a0033"]}, "storm", "Dark purple with sudden lightning."),
]
