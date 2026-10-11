"""Halloween 2026: slow, creeping reds. Ten patterns, about a minute each."""
from time import sleep
import math
import random
import time

import numpy as np

from lights import pixels, NUM_PIXELS, rotate

PATTERN_SECONDS = 60
FADE_SECONDS = 3
FPS = 30

# Colors as (R, G, B) in 0..1
RED = np.array([1.0, 0.0, 0.0])
CRIMSON = np.array([1.0, 0.0, 0.06])
EMBER = np.array([1.0, 0.14, 0.0])

x = np.arange(NUM_PIXELS)


def frames(seconds=PATTERN_SECONDS):
    """Yield (t, dt, fade) at about FPS for `seconds`.

    `fade` ramps 0 -> 1 -> 0 over the first and last FADE_SECONDS so patterns
    ease in and out instead of cutting.
    """
    start = last = time.time()
    while True:
        now = time.time()
        t = now - start
        if t >= seconds:
            return
        fade = min(1.0, t / FADE_SECONDS, (seconds - t) / FADE_SECONDS)
        yield t, now - last, fade
        last = now
        delay = 1 / FPS - (time.time() - now)
        if delay > 0:
            sleep(delay)


def show(rgb, fade=1.0):
    """Write an (N, 3) array of 0..1 colors to the strip."""
    rgb = np.clip(rgb, 0, 1) * (255 * fade)
    pixels[:] = rgb.astype(np.uint8).tolist()
    pixels.show()


def tint(intensity, color):
    return np.clip(intensity, 0, 1)[:, None] * color


def distance(a, b):
    """Distance between positions on the strip, wrapping around the ends."""
    return np.abs((a - b + NUM_PIXELS / 2) % NUM_PIXELS - NUM_PIXELS / 2)


def red_sweep():
    """The whole strip slowly swells from a low red glow to full red and back."""
    period = 12
    for t, dt, fade in frames():
        level = 0.05 + 0.95 * (0.5 - 0.5 * math.cos(2 * math.pi * t / period))
        show(tint(np.full(NUM_PIXELS, level), RED))


def upside_down_vines():
    """Vines creep out from random seeds, pulse, and slowly turn around the house."""
    vines = np.zeros(NUM_PIXELS)
    tips = []  # [position, direction, speed, length left]

    def sprout():
        seed = random.uniform(0, NUM_PIXELS)
        for direction in (-1, 1):
            tips.append([seed, direction, random.uniform(6, 12), random.uniform(25, 70)])

    for t, dt, fade in frames():
        while len(tips) < 10:
            sprout()
        vines *= 0.5 ** (dt / 6)
        heads = np.zeros(NUM_PIXELS)
        for tip in tips:
            step = tip[2] * dt
            tip[0] = (tip[0] + tip[1] * step) % NUM_PIXELS
            tip[2] *= 0.5 ** (dt / 10)  # growth slows as the vine ages
            tip[3] -= step
            vines[int(tip[0])] = 1.0
            heads += np.exp(-(distance(x, tip[0]) / 1.5) ** 2)
        tips[:] = [tip for tip in tips if tip[3] > 0]

        sway = 0.65 + 0.35 * np.sin(x * 0.35 - t * 1.5)
        rgb = tint(0.03 + vines * sway, CRIMSON) + tint(heads * 0.6, EMBER)
        show(np.roll(rgb, int(t * 2), axis=0), fade)


def heartbeat():
    """A slow lub-dub that ripples outward from five points around the house."""
    period = 60 / 50
    centers = np.linspace(0, NUM_PIXELS, 5, endpoint=False)
    from_center = np.min([distance(x, c) for c in centers], axis=0)
    for t, dt, fade in frames():
        phase = (t - from_center / 40) % period
        beat = (0.6 * np.exp(-((phase - 0.1) / 0.07) ** 2)
                + 0.4 * np.exp(-((phase - 0.4) / 0.09) ** 2))
        show(tint(0.06 + 0.5 * beat, CRIMSON), fade)


def ember_glow():
    """Every light smolders on its own, drifting between deep red and orange-red."""
    level = np.random.uniform(0.1, 0.5, NUM_PIXELS)
    target = level.copy()
    for t, dt, fade in frames():
        retarget = np.random.random(NUM_PIXELS) < dt * 0.7
        target[retarget] = np.random.uniform(0.05, 0.7, retarget.sum())
        level += (target - level) * min(1.0, dt * 1.5)
        show(tint(level, RED) + tint(level ** 2 * 0.15, np.array([0.0, 1.0, 0.0])), fade)


def blood_drips():
    """Drops slide along the strip, picking up speed and leaving a fading stain."""
    stain = np.zeros(NUM_PIXELS)
    drips = []  # [position, direction, speed, distance left]
    for t, dt, fade in frames():
        if len(drips) < 12 and random.random() < dt * 1.2:
            drips.append([random.uniform(0, NUM_PIXELS), random.choice((-1, 1)),
                          random.uniform(1, 3), random.uniform(30, 80)])
        stain *= 0.5 ** (dt / 4)
        drops = np.zeros(NUM_PIXELS)
        for drip in drips:
            drip[2] += 1.5 * dt
            step = drip[2] * dt
            drip[0] = (drip[0] + drip[1] * step) % NUM_PIXELS
            drip[3] -= step
            stain[int(drip[0])] = max(stain[int(drip[0])], 0.45)
            drops += np.exp(-(distance(x, drip[0]) / 1.2) ** 2)
        drips[:] = [drip for drip in drips if drip[3] > 0]
        show(tint(0.04 + stain + drops * 0.8, RED), fade)


def breathing_tide():
    """Long crimson swells roll around the house while the whole thing breathes."""
    for t, dt, fade in frames():
        swell = 0.5 + 0.5 * np.sin(2 * math.pi * (x / 120 - t / 10))
        breath = 0.6 + 0.4 * math.sin(2 * math.pi * t / 8)
        show(tint(0.08 + 0.55 * swell * breath, CRIMSON), fade)


def rifts():
    """Gates to the Upside Down slowly tear open, glow, and seal shut."""
    open_rifts = []  # [center, start, lifetime, width]
    next_rift = 0
    for t, dt, fade in frames():
        if t >= next_rift:
            open_rifts.append([random.uniform(0, NUM_PIXELS), t,
                               random.uniform(14, 20), random.uniform(20, 45)])
            next_rift = t + random.uniform(4, 7)
        open_rifts[:] = [r for r in open_rifts if t - r[1] < r[2]]
        glow = np.full(NUM_PIXELS, 0.03)
        for center, start, lifetime, width in open_rifts:
            opening = math.sin(math.pi * (t - start) / lifetime)
            edge = width * opening * (1 + 0.15 * np.sin(x * 0.7 + t * 2))
            core = np.clip(1 - distance(x, center) / np.maximum(edge, 1e-3), 0, 1)
            glow = np.maximum(glow, core ** 0.7 * 0.85)
        show(tint(glow, RED) + tint(glow ** 3 * 0.12, np.array([0.0, 1.0, 0.0])), fade)


def watching_eyes():
    """Pairs of red eyes open in the dark, blink now and then, and fade away."""
    eyes = []  # [position, start, lifetime, next blink]
    for t, dt, fade in frames():
        if len(eyes) < 7 and random.random() < dt * 0.8:
            eyes.append([random.randrange(NUM_PIXELS), t, random.uniform(6, 12),
                         t + random.uniform(2, 4)])
        eyes[:] = [e for e in eyes if t - e[1] < e[2]]
        glow = np.full(NUM_PIXELS, 0.02)
        for eye in eyes:
            position, start, lifetime, blink = eye
            age = t - start
            level = min(1.0, age / 1.5, (lifetime - age) / 1.5)
            if blink <= t < blink + 0.18:
                level *= 0.1
            elif t >= blink + 0.18:
                eye[3] = t + random.uniform(2, 5)
            for offset in (0, 1, 4, 5):
                glow[(position + offset) % NUM_PIXELS] = 0.9 * level
        show(tint(glow, RED), fade)


def lava():
    """Slow overlapping waves, like a red lava lamp wrapped around the house."""
    for t, dt, fade in frames():
        plasma = (np.sin(x * 0.045 + t * 0.35)
                  + np.sin(x * 0.11 - t * 0.23)
                  + np.sin(x * 0.023 + 2 * math.sin(t * 0.1)))
        level = 0.05 + 0.75 * ((plasma + 3) / 6) ** 2
        heat = 0.5 + 0.5 * np.sin(x * 0.03 - t * 0.17)
        show(level[:, None] * np.stack([np.ones(NUM_PIXELS), 0.1 * heat, 0.03 * (1 - heat)], axis=1), fade)


def orbiting_comets():
    """A few long-tailed comets circle the house at different speeds and directions."""
    comets = [(random.uniform(0, NUM_PIXELS), speed, tail)
              for speed, tail in ((9, 60), (-6, 80), (13, 45), (-11, 55))]
    for t, dt, fade in frames():
        glow = np.full(NUM_PIXELS, 0.03)
        for start, speed, tail in comets:
            head = start + speed * t
            behind = ((head - x) if speed > 0 else (x - head)) % NUM_PIXELS
            glow += np.exp(-3 * behind / tail) * 0.8
        show(tint(glow, CRIMSON), fade)


def joyce_wall():
    """Bulbs glow dim, and one at a time a bulb swells bright, as if spelling a message."""
    bulb_of = x // 6
    is_bulb = x % 6 < 2
    bulb_count = bulb_of.max() + 1
    warm = (np.arange(bulb_count) % 3 == 0)[bulb_of]  # every third bulb a touch orange
    lit = []  # [bulb, start]
    next_letter = 0
    for t, dt, fade in frames():
        if t >= next_letter:
            lit.append([random.randrange(bulb_count), t])
            next_letter = t + random.uniform(0.6, 1.4)
        lit[:] = [b for b in lit if t - b[1] < 2.4]
        bulbs = np.full(bulb_count, 0.12)
        for bulb, start in lit:
            bulbs[bulb] = max(bulbs[bulb], 0.12 + 0.8 * math.sin(math.pi * (t - start) / 2.4))
        level = np.where(is_bulb, bulbs[bulb_of], 0.0)
        show(tint(level, RED) + tint(level * warm * 0.12, np.array([0.0, 1.0, 0.0])), fade)


PATTERNS = [
    upside_down_vines,
    heartbeat,
    ember_glow,
    blood_drips,
    breathing_tide,
    rifts,
    watching_eyes,
    lava,
    orbiting_comets,
    joyce_wall,
]

if __name__ == "__main__":
    rotate(PATTERNS, seconds=PATTERN_SECONDS, scheduled=True)
