"""The bank of acts the song show (visualizer.py) picks from.

Every act is act(a, b, c) with three colors, returning draw(s), which takes
the moment `s` and returns an (N, 3) array of 0..1 colors. An act should answer
the beat and the sound, and show on any stretch of the house, since nobody
sees all of it at once. `s` has the time (now, dt), the sound (low, mid, high,
loud, bands), this frame's onsets (hits, and kicks for the bass ones), and
where the music is (beat, downbeat, count, bar, phase, beat_length).
"""
import math
import random

import numpy as np

from halloween26 import tint, distance, x
from lights import NUM_PIXELS

BEATS_PER_BAR = 4

RED = np.array([1.0, 0.0, 0.0])
EMBER = np.array([1.0, 0.14, 0.0])
ORANGE = np.array([1.0, 0.3, 0.0])
GOLD = np.array([1.0, 0.65, 0.15])
PURPLE = np.array([0.5, 0.0, 1.0])
MAGENTA = np.array([1.0, 0.0, 0.5])
GREEN = np.array([0.35, 1.0, 0.0])
PALE = np.array([0.55, 0.75, 1.0])
BLUE = np.array([0.1, 0.1, 1.0])
BONE = np.array([1.0, 0.85, 0.7])

PALETTES = [
    (RED, EMBER, BONE),  # blood
    (PURPLE, GREEN, PALE),  # poison
    (PURPLE, MAGENTA, GOLD),  # witch
    (BLUE, PURPLE, PALE),  # ghost
    (ORANGE, PURPLE, GOLD),  # pumpkin
    (GREEN, RED, GOLD),  # swamp
    (RED, PURPLE, GOLD),  # hellfire
    (MAGENTA, BLUE, PALE),  # phantom
    (GREEN, PURPLE, BONE),  # zombie
    (ORANGE, RED, BONE),  # bonfire
    (BLUE, GREEN, GOLD),  # deep sea
    (PURPLE, RED, GREEN),  # cursed
]


def panels(count, shift=0):
    """How far each light is from the center of its stretch of house, with `count` stretches."""
    width = NUM_PIXELS / count
    return np.abs((x + shift) % width - width / 2)


# Quiet acts


def fog_and_sparks(a, b, c):
    """Fog drifts around the house, breathing with the bass, and sparks catch on the notes."""
    sparks = np.zeros(NUM_PIXELS)
    drift = [random.uniform(0, 9)]

    def draw(s):
        drift[0] += s.dt * (0.15 + 0.6 * s.low)
        fog = 0.5 + 0.5 * np.sin(x * 0.045 - drift[0]) * np.sin(x * 0.017 + drift[0] * 0.6)
        for strength in s.hits:
            sparks[random.randrange(NUM_PIXELS)] = 0.4 + 0.6 * strength
        sparks[:] *= 0.5 ** (s.dt / 0.25)
        return tint(fog * (0.05 + 0.35 * s.low), a) + tint((1 - fog) * (0.03 + 0.2 * s.mid), b) + tint(sparks, c)
    return draw


def eyes_in_the_dark(a, b, c):
    """Pairs of eyes open on the notes, stare, blink and close."""
    eyes = []  # [position, age, strength]

    def draw(s):
        for strength in s.hits:
            if strength > 0.2 and len(eyes) < 10:
                eyes.append([random.randrange(NUM_PIXELS), 0.0, 0.6 + 0.4 * strength])
        rgb = tint(np.full(NUM_PIXELS, 0.02 + 0.1 * s.low), a)
        for eye in eyes:
            eye[1] += s.dt
            position, age, strength = eye
            level = strength * min(1.0, age / 0.15, max(0.0, (3.5 - age) / 0.8))
            if 1.6 < age % 2.2 < 1.75:  # blink
                level *= 0.1
            for offset in (0, 1, 5, 6):
                rgb[(position + offset) % NUM_PIXELS] += c * level
        eyes[:] = [e for e in eyes if e[1] < 3.5]
        return rgb
    return draw


def creeping_tendrils(a, b, c):
    """Tendrils lurch out from around the house a little further on every beat, leaving a glowing trail."""
    trail = np.zeros(NUM_PIXELS)
    count = 8
    roots = (np.arange(count) + 0.5) * NUM_PIXELS / count
    lengths = np.zeros(count * 2)
    targets = np.zeros(count * 2)
    sides = np.array([-1, 1] * count)
    origins = np.repeat(roots, 2)

    def draw(s):
        if s.beat:
            targets[:] += np.random.uniform(4, 11, len(targets))
        lengths[:] += (targets - lengths) * min(1.0, s.dt * 14)
        grown = lengths >= NUM_PIXELS / count / 2
        lengths[grown] = targets[grown] = 0
        trail[:] *= 0.5 ** (s.dt / 0.45)
        tips = ((origins + sides * lengths) % NUM_PIXELS).astype(int)
        trail[tips] = 1
        heads = np.zeros(NUM_PIXELS)
        heads[tips] = 0.5 + 0.5 * s.loud
        return tint(trail * (0.35 + 0.5 * s.loud), a) + tint(trail ** 4 * 0.4, b) + tint(heads, c) + tint(
            np.full(NUM_PIXELS, 0.015), a)
    return draw


def bleeding_veins(a, b, c):
    """Blood swells outward from eight places with the bass, leaving a bright edge that falls back slowly."""
    d = panels(8)
    edge = [0.0]
    reach = NUM_PIXELS / 16

    def draw(s):
        height = s.low ** 1.5 * reach
        edge[0] = max(height, edge[0] - s.dt * 35)
        inside = np.clip(height - d + 1, 0, 1)
        rim = np.exp(-((d - edge[0]) / 1.2) ** 2)
        return tint(inside * (0.15 + 0.6 * (1 - d / reach)), a) + tint(inside * (d / reach) * 0.5, b) + tint(
            rim * (0.15 + 0.6 * s.mid), c)
    return draw


# Middle acts


def graveyard_march(a, b, c):
    """Blocks of light march around the house, one step on each beat, turning back every two bars."""
    period = NUM_PIXELS / 16
    position = [0.0]
    direction = [1]

    def draw(s):
        if s.downbeat and s.bar % 2 == 0:
            direction[0] *= -1
        if s.beat:
            position[0] += direction[0] * period / 2
        step = position[0] + direction[0] * period / 2 * (min(1.0, s.phase * 3.5) - 1)
        spots = (x - step) / period
        cell = spots % 1
        block = np.clip(10 * (0.42 - np.abs(cell - 0.5)), 0, 1) * (0.2 + 0.5 * s.loud + 0.3 * (1 - s.phase) ** 2)
        odd = np.floor(spots) % 2
        return tint(block * odd, a) + tint(block * (1 - odd), b) + tint(np.full(NUM_PIXELS, 0.01), a) + tint(
            block * (1 - s.phase) ** 4 * 0.4, c)
    return draw


def spectrum_tombstones(a, b, c):
    """Twelve glowing columns, each a different part of the sound, that move along every four bars."""
    columns = 12
    width = NUM_PIXELS / columns
    reach = width / 2 - 2
    band_of = np.array([0, 4, 1, 6, 2, 5, 0, 7, 3, 6, 1, 4])
    ramp = np.linspace(0, 1, 8)[:, None]
    colors = np.where(ramp < 0.5, a * (1 - ramp * 2) + b * ramp * 2, b * (2 - ramp * 2) + c * (ramp * 2 - 1))
    heights = np.zeros(8)
    caps = np.zeros(8)
    d = np.abs(x % width - width / 2)
    column = (x // width).astype(int)

    def draw(s):
        heights[:] = np.maximum(s.bands ** 1.3, heights * 0.5 ** (s.dt / 0.12))
        caps[:] = np.maximum(heights, caps - s.dt * 0.7)
        band = band_of[(column + s.bar // 4) % columns]
        body = np.clip(heights[band] * reach - d + 1, 0, 1) * (0.25 + 0.65 * (1 - d / reach))
        cap = np.exp(-((d - caps[band] * reach) / 0.8) ** 2) * 0.6 * (caps[band] > 0.05)
        return np.clip(body + cap, 0, 1)[:, None] * colors[band]
    return draw


def witch_fire(a, b, c):
    """Flames climb outward from ten fires, fed by the bass and thrown high on the beats."""
    count = 10
    width = NUM_PIXELS / count
    d = panels(count).astype(int)
    which = (x // width).astype(int)
    heat = np.zeros((count, int(width / 2) + 2))
    points = [0, 0.3, 0.65, 1]
    colors = [np.zeros(3), a * 0.7, b * 0.5 + a * 0.5, c]
    table = np.stack([np.interp(np.linspace(0, 1, 64), points, [color[i] for color in colors]) for i in range(3)], axis=1)
    climb = [0.0]
    kick = [0.0]

    def draw(s):
        if s.beat:
            kick[0] = 1.0
        kick[0] *= 0.5 ** (s.dt / 0.2)
        climb[0] += s.dt * (35 + 60 * s.low)
        steps = int(climb[0])
        climb[0] -= steps
        for _ in range(min(steps, 6)):
            heat[:, 1:] = heat[:, :-1] * np.random.uniform(0.84, 0.99, (count, heat.shape[1] - 1))
            heat[:, 0] = np.random.uniform(0.3, 1.0, count) * (0.25 + 0.75 * s.low + 0.4 * kick[0])
        return table[(np.clip(heat[which, d], 0, 1) * 63).astype(int)]
    return draw


def jack_o_lanterns(a, b, c):
    """Ten jack-o'-lanterns chomp in turn around the house, one on each beat, with green vines between them."""
    count = 10
    size = NUM_PIXELS // count
    which = x // size
    d = np.abs(x % size - size / 2)
    vine = (d > size / 2 - 2).astype(float)
    flare = np.zeros(count)
    flame = np.ones(count)
    chomp = np.zeros(count)

    def draw(s):
        if s.beat:
            chomp[s.count % count] = 1.0
            flare[s.count % count] = 0.8
        chomp[:] *= 0.5 ** (s.dt / 0.15)
        for strength in s.hits:
            if strength > 0.25:
                flare[random.randrange(count)] = strength
        flare[:] *= 0.5 ** (s.dt / 0.25)
        flame[:] += (np.random.uniform(0.7, 1.0, count) - flame) * min(1.0, s.dt * 8)
        mouth = np.clip(5 + 4 * s.low + 11 * chomp[which] - d, 0, 1) * (1 - d / size)
        level = (0.2 + 0.5 * s.low + 0.5 * flare) * flame
        return tint(mouth * level[which], ORANGE) + tint(mouth * flare[which] * 0.5, GOLD) + tint(
            vine * (0.04 + 0.15 * s.loud), GREEN)
    return draw


def reapers_scythe(a, b, c):
    """A field of color lit by the bass, with two dark blades sweeping through it every two bars."""
    gap = NUM_PIXELS / 2

    def draw(s):
        where = (s.count + s.phase) / (BEATS_PER_BAR * 2) * gap
        behind = (where - x) % gap
        dark = np.clip(behind / 70, 0, 1) ** 2
        edge = np.exp(-(behind / 2.0) ** 2)
        field = 0.5 + 0.5 * np.sin(x * 0.05 + s.now * 0.5)
        level = (0.12 + 0.6 * s.low) * dark
        return tint(field * level, a) + tint((1 - field) * level, b) + tint(edge * (0.5 + 0.5 * s.loud), c)
    return draw


# Loud acts


def serpents(a, b, c):
    """Three long serpents race around the house with the bass, turning every four bars."""
    heads = np.array([0.0, NUM_PIXELS / 3, NUM_PIXELS * 2 / 3])
    direction = [1]
    strike = [0.0]
    tail_length = 26

    def draw(s):
        if s.downbeat and s.bar % 4 == 0:
            direction[0] *= -1
        if s.hits:
            strike[0] = max(strike[0], max(s.hits))
        strike[0] *= 0.5 ** (s.dt / 0.12)
        heads[:] += s.dt * direction[0] * (40 + 200 * s.low)
        rgb = tint(np.full(NUM_PIXELS, 0.015), a)
        for i, head in enumerate(heads):
            tail = (head - x) * direction[0] % NUM_PIXELS
            body = np.exp(-tail / tail_length) * (0.75 + 0.25 * np.sin(tail * 0.7 - s.now * 9))
            rgb += tint(body * (0.3 + 0.6 * s.loud), b if i == 1 else a)
            rgb += tint(np.exp(-(tail / 2.5) ** 2) * (0.4 + 0.6 * strike[0]), c)
        return rgb
    return draw


def shockwaves(a, b, c):
    """Every beat throws a ring out from four places around the house, and they move along each bar."""
    count = 4
    reach = NUM_PIXELS / count / 2
    rings = []  # [start, color, strength]
    colors = [a, b, c]
    fired = [0]

    def draw(s):
        if s.beat:
            rings.append([s.now, colors[fired[0] % 3], 1.0 if s.downbeat else 0.7])
            fired[0] += 1
        d = panels(count, s.bar * 25)
        rgb = tint(np.full(NUM_PIXELS, 0.02 + 0.12 * s.low), a)
        for start, color, strength in rings:
            age = s.now - start
            wave = np.exp(-((d - age / max(s.beat_length, 0.25) * reach * 0.9) / 6) ** 2)
            rgb += tint(wave * strength * (0.4 + 0.6 * s.loud) * math.exp(-age / 0.9), color)
        rings[:] = [r for r in rings if s.now - r[0] < 1.8]
        return rgb
    return draw


def bone_chase(a, b, c):
    """The house is cut in ten; pieces snap on with the beat, chasing around, then jumping across."""
    count = 10
    which = x // (NUM_PIXELS // count)
    glow = np.zeros(count)
    tints = np.tile(a, (count, 1))
    gaps = (x % (NUM_PIXELS // count) >= 3).astype(float)
    spot = [0]

    def light(i, color):
        glow[i % count] = 1
        tints[i % count] = color

    def draw(s):
        if s.beat:
            kind = s.bar // 2 % 3
            spot[0] += (1, -1, 3)[kind]
            light(spot[0], b if s.count % 2 else a)
            if s.downbeat:
                light(spot[0] + count // 2, c)
        for strength in s.hits:
            if strength > 0.4:
                light(random.randrange(count), b)
        glow[:] *= 0.5 ** (s.dt / 0.13)
        return (glow[which] * gaps * (0.5 + 0.5 * s.loud))[:, None] * tints[which] + tint(np.full(NUM_PIXELS, 0.01 + 0.06 * s.low), a)
    return draw


def lightning_riot(a, b, c):
    """A dark sky throbbing with the bass, with jagged bolts tearing through it on the big hits."""
    charge = np.zeros(NUM_PIXELS)

    def draw(s):
        for strength in s.hits:
            if strength > 0.3:
                start = random.randrange(NUM_PIXELS)
                bolt = (start + np.arange(random.randint(12, 55))) % NUM_PIXELS
                charge[bolt] = np.maximum(charge[bolt], np.random.uniform(0.2, 1.0, len(bolt)) * (0.5 + 0.5 * strength))
        charge[:] *= 0.5 ** (s.dt / 0.07)
        swell = 0.5 + 0.5 * np.sin(x * 0.03 + s.now * 1.2)
        return tint(swell * (0.03 + 0.35 * s.low), a) + tint((1 - swell) * (0.02 + 0.2 * s.low), b) + tint(charge, c)
    return draw


def kaleidoscope(a, b, c):
    """Mirrored patterns pour out from six places, faster with the bass and kicked on with each beat."""
    d = panels(6)
    flow = [0.0]

    def draw(s):
        flow[0] += s.dt * (0.6 + 3 * s.low) + (0.5 if s.beat else 0)
        first = 0.5 + 0.5 * np.sin(d * 0.25 - flow[0])
        second = 0.5 + 0.5 * np.sin(d * 0.11 + flow[0] * 0.7 + s.bar * 2)
        return tint(first ** 3 * (0.2 + 0.7 * s.loud), a) + tint(second ** 4 * (0.2 + 0.6 * s.mid), b) + tint(
            (first * second) ** 6 * (0.2 + 0.8 * s.high), c)
    return draw


# More quiet acts


def near(where, period):
    """How far each light is from the nearest of a row of spots `period` apart."""
    return np.abs((x - where + period / 2) % period - period / 2)


def moonrise(a, b, c):
    """Pale moons drift around the house, their halos swelling with the bass as clouds cross them."""
    period = NUM_PIXELS / random.choice((2, 3, 4))
    where = [random.uniform(0, period)]
    way = random.choice((-1, 1))
    pulse = [0.0]

    def draw(s):
        if s.beat:
            pulse[0] = 1.0
        pulse[0] *= 0.5 ** (s.dt / 0.2)
        where[0] += way * s.dt * (5 + 30 * s.low)
        d = near(where[0], period)
        cloud = 0.55 + 0.45 * np.sin(x * 0.09 + s.now * 0.8) * np.sin(x * 0.031 - s.now * 0.4)
        halo = np.exp(-(d / (14 + 30 * s.low)) ** 2) * cloud
        return tint(halo * (0.12 + 0.55 * s.low + 0.3 * pulse[0]), a) + tint(np.exp(-(d / 6) ** 2) * (0.3 + 0.6 * s.mid), c) + tint(
            np.full(NUM_PIXELS, 0.015), b)
    return draw


def wandering_wisps(a, b, c):
    """Soft lights wander the dark, darting somewhere new on each beat and brightening with the melody."""
    count = random.choice((6, 8, 10))
    where = np.random.uniform(0, NUM_PIXELS, count)
    speed = np.random.uniform(-30, 30, count)

    def draw(s):
        if s.beat:
            speed[:] = np.random.uniform(-90, 90, count)
        speed[:] *= 0.5 ** (s.dt / 0.35)
        where[:] += speed * s.dt * (0.5 + 1.5 * s.low)
        rgb = tint(np.full(NUM_PIXELS, 0.012 + 0.05 * s.low), a)
        for i in range(count):
            glow = np.exp(-(distance(x, where[i]) / (2.5 + 3 * s.mid)) ** 2) * (0.25 + 0.75 * s.mid)
            rgb += tint(glow, c if i % 3 == 0 else b)
        return rgb
    return draw


def candle_row(a, b, c):
    """A row of candles shivers with the bass; the beat flares one and the bar snuffs a few out."""
    count = random.choice((16, 20, 25))
    size = NUM_PIXELS // count
    which = x // size
    d = np.abs(x % size - size / 2)
    shape = np.exp(-(d / 2.2) ** 2)
    level = np.ones(count) * 0.5
    flicker = np.ones(count)

    def draw(s):
        if s.beat:
            level[random.randrange(count)] = 1.3
        if s.downbeat:
            level[np.random.randint(0, count, 3)] = 0.0
        level[:] += (0.5 - level) * min(1.0, s.dt * 1.8)
        flicker[:] += (np.random.uniform(0.5, 1.0, count) - flicker) * min(1.0, s.dt * 14)
        lit = level * flicker * (0.35 + 1.1 * s.low)
        return tint(shape * lit[which], a) + tint(shape ** 4 * lit[which] * 0.8, c) + tint(np.exp(-(d / 6) ** 2) * lit[which] * 0.12, b)
    return draw


def plucked_strings(a, b, c):
    """Spider silk strung around the house, each thread shaking when a note plucks it."""
    count = random.choice((5, 6, 8))
    width = NUM_PIXELS / count
    which = (x // width).astype(int)
    u = x % width / width
    modes = np.random.randint(2, 7, count)
    shake = np.zeros(count)

    def draw(s):
        for strength in s.hits:
            if strength > 0.15:
                shake[random.randrange(count)] = 0.45 + 0.55 * strength
        if s.downbeat:
            shake[:] = np.maximum(shake, 0.5)
        shake[:] *= 0.5 ** (s.dt / 0.4)
        wobble = np.abs(np.sin(math.pi * modes[which] * u)) * np.abs(np.cos(s.now * (7 + modes[which] * 3)))
        return tint(wobble * shake[which], c) + tint(wobble ** 2 * shake[which] * 0.6, b) + tint(np.full(NUM_PIXELS, 0.02 + 0.06 * s.low), a)
    return draw


def heartbeat_monitor(a, b, c):
    """A flat line around the house, and every beat sends a sharp blip racing along it."""
    period = NUM_PIXELS / random.choice((3, 4, 5))
    way = random.choice((-1, 1))
    blips = []

    def draw(s):
        if s.beat:
            blips.append([s.now, random.uniform(0, period), 1.0 if s.downbeat else 0.7])
        rgb = tint(np.full(NUM_PIXELS, 0.02 + 0.05 * s.low), a)
        for start, origin, strength in blips:
            tail = (way * (origin + (s.now - start) * 75 - x)) % period
            level = strength * (0.5 + 0.5 * s.loud)
            rgb += tint(np.exp(-(tail / 1.5) ** 2) * level, c)
            rgb += tint((np.exp(-((tail - 6) / 2.5) ** 2) * 0.6 + np.exp(-tail / 20) * 0.3) * level, a)
        blips[:] = [p for p in blips if s.now - p[0] < 1.0]
        return rgb
    return draw


def passing_ghosts(a, b, c):
    """Ghosts appear with the beat and glide through the house, shimmering with the high notes."""
    ghosts = []  # [position, speed, age]

    def draw(s):
        if s.beat and s.count % 2 == 0 and len(ghosts) < 7:
            ghosts.append([random.uniform(0, NUM_PIXELS), random.choice((-1, 1)) * random.uniform(35, 90), 0.0])
        rgb = tint(np.full(NUM_PIXELS, 0.015 + 0.08 * s.low), a)
        for ghost in ghosts:
            ghost[0] += ghost[1] * s.dt * (0.6 + s.low)
            ghost[2] += s.dt
            life = min(1.0, ghost[2] / 0.3, max(0.0, 3.5 - ghost[2]))
            d = distance(x, ghost[0])
            shimmer = 0.75 + 0.25 * np.sin(x * 1.3 + s.now * 18) * s.high
            rgb += tint(np.exp(-(d / 13) ** 2) * shimmer * life * (0.3 + 0.6 * s.mid + 0.3 * s.low), b)
            rgb += tint(np.exp(-(d / 5) ** 2) * life * (0.25 + 0.5 * s.loud), c)
        ghosts[:] = [g for g in ghosts if g[2] < 3.5]
        return rgb
    return draw


def dripping_ooze(a, b, c):
    """Fat drops swell and run along the lights, faster and faster, on the bass and the notes."""
    drops = []  # [position, speed, distance left]
    way = random.choice((-1, 1))
    puddle = np.zeros(NUM_PIXELS)

    def draw(s):
        if len(drops) < 8:
            for strength in s.kicks:
                if strength > 0.2:
                    drops.append([random.uniform(0, NUM_PIXELS), 10.0, random.uniform(30, 70)])
        puddle[:] *= 0.5 ** (s.dt / 0.2)
        for drop in drops:
            drop[1] += s.dt * (70 + 220 * s.low)
            step = drop[1] * s.dt
            drop[0] += way * step
            drop[2] -= step
            spots = (drop[0] - way * np.arange(5)).astype(int) % NUM_PIXELS
            puddle[spots] = np.maximum(puddle[spots], 1 - np.arange(5) * 0.18)
        drops[:] = [d for d in drops if d[2] > 0]
        return tint(puddle * (0.4 + 0.6 * s.low), a) + tint(puddle ** 5 * s.loud, c) + tint(np.full(NUM_PIXELS, 0.015 + 0.08 * s.low), b)
    return draw


def crawling_cracks(a, b, c):
    """The dark splits open: jagged cracks tear outward on the bass and glow before they seal."""
    glow = np.zeros(NUM_PIXELS)
    cracks = []  # [origin, reach, limit]

    def draw(s):
        for strength in s.kicks + s.hits[:1]:
            if strength > 0.15 and len(cracks) < 10:
                cracks.append([random.randrange(NUM_PIXELS), 0.0, random.uniform(10, 45)])
        glow[:] *= 0.5 ** (s.dt / (0.25 + 0.3 * (1 - s.loud)))
        for crack in cracks:
            crack[1] += s.dt * 130
            for side in (-1, 1):
                glow[int(crack[0] + side * crack[1]) % NUM_PIXELS] = random.uniform(0.45, 1.0)
        cracks[:] = [k for k in cracks if k[1] < k[2]]
        return tint(glow, a) + tint(glow ** 3, c) + tint(np.full(NUM_PIXELS, 0.012 + 0.05 * s.low), b)
    return draw


# More middle acts


def skeleton_ribs(a, b, c):
    """Rows of ribs sway from side to side with the beat, swelling with the bass."""
    spacing = random.choice((10, 14, 20))
    d = panels(random.choice((4, 5, 8)))
    reach = d.max()
    sway = [0.0]

    def draw(s):
        aim = spacing / 4 * (1 if s.count % 2 else -1)
        sway[0] += (aim - sway[0]) * min(1.0, s.dt * 18)
        ribs = np.clip(1.5 - near(sway[0], spacing), 0, 1)
        body = np.clip((0.35 + 0.85 * s.low) * reach + 2 - d, 0, 1)
        return tint(ribs * body * (0.25 + 0.75 * s.loud), c) + tint(ribs * (1 - body) * 0.12, a) + tint(body * (0.03 + 0.1 * s.low), b)
    return draw


def bat_flock(a, b, c):
    """Flocks of bats flap around the house, racing with the bass and scattering on the hits."""
    flocks = random.choice((2, 3, 4))
    bats = 45
    groups = np.arange(bats) % flocks * NUM_PIXELS / flocks
    offsets = np.random.normal(0, 9, bats)
    flaps = np.random.uniform(0, 6.3, bats)
    where = [0.0]
    way = [random.choice((-1, 1))]
    scatter = [1.0]

    def draw(s):
        if s.downbeat and s.bar % 2 == 0:
            way[0] *= -1
        if s.hits and max(s.hits) > 0.35:
            scatter[0] = 2.6
        scatter[0] += (1 - scatter[0]) * min(1.0, s.dt * 4)
        where[0] += way[0] * s.dt * (35 + 260 * s.low)
        spots = (where[0] + groups + offsets * scatter[0]).astype(int) % NUM_PIXELS
        wings = 0.5 + 0.5 * np.sin(s.now * 26 + flaps)
        rgb = tint(np.full(NUM_PIXELS, 0.015 + 0.08 * s.low), a)
        np.add.at(rgb, spots, wings[:, None] * b * (0.4 + 0.6 * s.loud))
        np.add.at(rgb, (spots + 1) % NUM_PIXELS, wings[:, None] * c * 0.35)
        return rgb
    return draw


def pendulum(a, b, c):
    """Blades swing across each stretch of house, reaching the end of the swing exactly on the beat."""
    count = random.choice((3, 4, 5))
    width = NUM_PIXELS / count
    u = x % width
    trail = np.zeros(NUM_PIXELS)

    def draw(s):
        where = width / 2 + (width / 2 - 3) * math.cos(math.pi * (s.count + s.phase))
        blade = np.exp(-((u - where) / 2.5) ** 2)
        trail[:] = np.maximum(trail * 0.5 ** (s.dt / 0.12), blade)
        strike = (1 - s.phase) ** 4
        return tint(trail * (0.25 + 0.65 * s.loud), a) + tint(blade * (0.5 + 0.5 * strike), c) + tint(
            np.exp(-((u - where) / 14) ** 2) * (0.08 + 0.3 * s.low), b)
    return draw


def cauldron_bubbles(a, b, c):
    """A cauldron heaves with the bass, and the notes blow bubbles that swell and burst."""
    bubbles = []  # [position, age, size]

    def draw(s):
        for strength in s.hits:
            if strength > 0.15 and len(bubbles) < 12:
                bubbles.append([random.uniform(0, NUM_PIXELS), 0.0, 5 + 15 * strength])
        heave = 0.5 + 0.5 * np.sin(x * 0.06 + s.now * (0.7 + 2.5 * s.low))
        rgb = tint(heave * (0.05 + 0.4 * s.low), a)
        for bubble in bubbles:
            bubble[1] += s.dt
            ring = bubble[1] / 0.45 * bubble[2]
            d = distance(x, bubble[0])
            rgb += tint(np.exp(-((d - ring) / 1.3) ** 2) * (1 - bubble[1] / 0.45), c)
            rgb += tint(np.clip(ring - d, 0, 1) * 0.25, b)
        bubbles[:] = [p for p in bubbles if p[1] < 0.45]
        return rgb
    return draw


def vu_ladder(a, b, c):
    """Stepped meters climb the house, each one a part of the sound, going from dark colors to bright."""
    count = 8
    width = NUM_PIXELS / count
    which = (x // width).astype(int)
    rungs = random.choice((6, 8, 10))
    u = x % width / width
    u = np.where(which % 2, 1 - u, u)  # every other meter runs the other way, so they meet
    rung = (u * rungs).astype(int)
    gaps = (u * rungs % 1 < 0.8).astype(float)
    ramp = (rung / max(1, rungs - 1))[:, None]
    colors = np.where(ramp < 0.5, a * (1 - ramp * 2) + b * ramp * 2, b * (2 - ramp * 2) + c * (ramp * 2 - 1))
    levels = np.zeros(count)
    peaks = np.zeros(count)
    order = np.random.permutation(count)

    def draw(s):
        levels[:] = np.maximum(s.bands[order] ** 1.2, levels * 0.5 ** (s.dt / 0.1))
        peaks[:] = np.maximum(levels, peaks - s.dt * 0.5)
        lit = (rung < levels[which] * rungs).astype(float) * 0.8
        lit += (rung == (peaks[which] * rungs).astype(int)) * 0.7
        return colors * (lit * gaps)[:, None]
    return draw


def haunted_piano(a, b, c):
    """Keys all around the house strike whenever their part of the music jumps, like a ghost at the organ."""
    keys = random.choice((24, 32, 40))
    size = NUM_PIXELS // keys
    which = np.minimum(x // size, keys - 1)
    gaps = (x % size < size - 2).astype(float)
    band_of = np.resize(np.random.permutation(8), keys)
    glow = np.zeros(keys)
    before = np.zeros(8)
    ramp = (band_of / 7)[:, None]
    colors = np.where(ramp < 0.5, a * (1 - ramp * 2) + b * ramp * 2, b * (2 - ramp * 2) + c * (ramp * 2 - 1))

    def draw(s):
        rising = np.maximum(0, s.bands - before)
        before[:] = s.bands
        glow[:] = np.maximum(glow * 0.5 ** (s.dt / 0.16), np.clip(rising[band_of] * 9, 0, 1))
        return (glow[which] * gaps)[:, None] * colors[which] + tint(gaps * (0.008 + 0.05 * s.low), a)
    return draw


def braided_serpents(a, b, c):
    """Two sets of bright coils slide through each other, and they blaze wherever they cross."""
    turns = random.choice((6, 8, 12))
    wave = 2 * math.pi * turns / NUM_PIXELS
    flow = [0.0]

    def draw(s):
        flow[0] += s.dt * (20 + 110 * s.low) + (5 if s.beat else 0)
        one = (0.5 + 0.5 * np.cos(wave * (x - flow[0]))) ** 6
        two = (0.5 + 0.5 * np.cos(wave * (x + flow[0]))) ** 6
        return tint(one * (0.25 + 0.7 * s.loud), a) + tint(two * (0.25 + 0.7 * s.mid), b) + tint((one * two) ** 0.5 * (0.5 + 0.5 * s.high), c)
    return draw


def falling_souls(a, b, c):
    """Souls streak around the house on the notes, trailing long tails, bigger on the bigger hits."""
    way = random.choice((-1, 1))
    souls = []  # [position, speed, tail, life, color]

    def draw(s):
        for strength in s.hits:
            if strength > 0.15 and len(souls) < 10:
                souls.append([random.uniform(0, NUM_PIXELS), random.uniform(90, 200) * (0.6 + strength), 6 + 28 * strength, 1.0,
                              random.choice((a, b))])
        rgb = tint(np.full(NUM_PIXELS, 0.012 + 0.07 * s.low), a)
        for soul in souls:
            soul[0] += way * soul[1] * s.dt
            soul[3] -= s.dt
            tail = way * (soul[0] - x) % NUM_PIXELS
            life = min(1.0, soul[3] * 3)
            rgb += tint(np.exp(-tail / soul[2]) * life * 0.9, soul[4]) + tint(np.exp(-(tail / 1.5) ** 2) * life, c)
        souls[:] = [p for p in souls if p[3] > 0]
        return rgb
    return draw


def snapping_jaws(a, b, c):
    """Jaws snap shut all around the house on every beat, then slowly creep open."""
    count = random.choice((4, 5, 6, 8))
    d = panels(count)
    edge = d.max() - d
    teeth = random.choice((3, 4, 6))
    tooth = (x % (teeth * 2) < teeth).astype(float)

    def draw(s):
        bite = (1 - s.phase) ** 3
        reach = d.max() * (0.1 + 0.9 * bite) + 6 * s.low
        tips = np.clip(reach + teeth - edge, 0, 1) * tooth
        body = np.clip(reach - edge, 0, 1)
        return tint(body * (0.3 + 0.6 * s.loud), a) + tint((tips - body).clip(0, 1) * 0.9, c) + tint(body * bite * 0.5, b)
    return draw


def ghost_train(a, b, c):
    """Trains of lit carriages chug around the house in time, one step on every beat, headlamps blazing."""
    period = NUM_PIXELS / random.choice((3, 4, 5))
    step = random.choice((10, 14, 18))
    car = random.choice((7, 9))
    length = car * random.choice((3, 4, 5))
    way = random.choice((-1, 1))

    def draw(s):
        where = (s.count + min(1.0, s.phase * 2)) * step * way
        u = way * (where - x) % period
        train = (u < length).astype(float)
        cars = ((u % car) < car - 2) * train
        kick = (1 - s.phase) ** 2
        return tint(cars * (0.2 + 0.5 * s.loud + 0.3 * kick), a) + tint(cars * (u % car > 1) * (u % car < 4) * (0.15 + 0.8 * s.mid), b) + tint(
            np.exp(-(u / 2) ** 2) * (0.5 + 0.5 * kick), c)
    return draw


def haunted_windows(a, b, c):
    """A row of lit windows: the beat switches them on and off, and something crosses behind them."""
    count = random.choice((10, 14, 20))
    size = NUM_PIXELS // count
    which = np.minimum(x // size, count - 1)
    pane = (x % size < size - 4).astype(float)
    on = np.random.random(count) < 0.4
    glow = on.astype(float)
    figure = [random.uniform(0, NUM_PIXELS)]

    def draw(s):
        if s.beat:
            on[np.random.randint(0, count, 2 + s.bar % 4)] = np.random.random(2 + s.bar % 4) < 0.55
        glow[:] += (on - glow) * min(1.0, s.dt * 22)
        figure[0] += s.dt * (25 + 170 * s.low)
        shadow = np.clip(distance(x, figure[0]) / 7, 0, 1)
        level = glow[which] * pane * shadow * (0.3 + 0.7 * s.loud)
        return tint(level, c) + tint(level * s.low * 0.8, a) + tint(pane * (0.008 + 0.04 * s.mid), b)
    return draw


def storm_clouds(a, b, c):
    """Great clouds light up from inside, each with its own part of the sound, and burst on the bass."""
    count = random.choice((6, 8))
    centers = (np.arange(count) + 0.5) * NUM_PIXELS / count
    shapes = np.stack([np.exp(-(distance(x, p) / (NUM_PIXELS / count / 2.4)) ** 2) for p in centers])
    order = np.random.permutation(8)[:count]
    burst = np.zeros(count)

    def draw(s):
        for strength in s.kicks:
            if strength > 0.2:
                burst[random.randrange(count)] = 0.5 + 0.5 * strength
        burst[:] *= 0.5 ** (s.dt / 0.12)
        roll = 0.75 + 0.25 * np.sin(x * 0.2 + s.now * 2)
        inner = (s.bands[order] ** 1.5)[:, None] * shapes
        flash = burst[:, None] * shapes
        return tint(inner.sum(axis=0) * roll * 0.65, a) + tint(flash.sum(axis=0), c) + tint(inner.max(axis=0) ** 3 * 0.4, b)
    return draw


# More loud acts


def implosion(a, b, c):
    """Rings of light get sucked inward with the beat, then the bar blows it all back out."""
    d = panels(random.choice((3, 4, 5, 6)))
    spacing = random.choice((14, 20, 28))
    burst = [9.0]

    def draw(s):
        if s.downbeat:
            burst[0] = 0.0
        burst[0] += s.dt
        rings = (0.5 + 0.5 * np.cos(2 * math.pi * (d / spacing + s.count + s.phase))) ** 4
        blast = np.exp(-((d - burst[0] * 110) / 7) ** 2) * math.exp(-burst[0] / 0.35)
        return tint(rings * (0.2 + 0.6 * s.low), a) + tint(rings ** 3 * (0.1 + 0.6 * s.high), b) + tint(blast, c)
    return draw


def buzzsaw(a, b, c):
    """A saw blade screams around the house, spinning up with the bass and reversing every two bars."""
    period = random.choice((20, 25, 40, 50))
    spot = [0.0]
    way = [random.choice((-1, 1))]

    def draw(s):
        if s.downbeat and s.bar % 2 == 0:
            way[0] *= -1
        spot[0] += way[0] * s.dt * (40 + 520 * s.low)
        ramp = ((x - spot[0]) * way[0] / period) % 1
        kick = (1 - s.phase) ** 3
        return tint(ramp ** 2 * (0.2 + 0.6 * s.loud + 0.2 * kick), a) + tint(ramp ** 10 * (0.6 + 0.4 * kick), c) + tint(
            (1 - ramp) ** 6 * 0.3 * s.mid, b)
    return draw


def soul_burst(a, b, c):
    """Each big beat bursts into sparks that fly out both ways, slow down and burn out."""
    most = 150
    where = np.zeros(most)
    speed = np.zeros(most)
    life = np.zeros(most)
    next_one = [0]

    def burst(strength):
        fresh = (next_one[0] + np.arange(16)) % most
        next_one[0] = (next_one[0] + 16) % most
        where[fresh] = random.uniform(0, NUM_PIXELS)
        speed[fresh] = np.random.uniform(-130, 130, 16) * (0.5 + strength)
        life[fresh] = np.random.uniform(0.5, 1.0, 16)

    def draw(s):
        if s.beat:
            burst(0.5 + 0.5 * s.loud)
        for strength in s.kicks:
            if strength > 0.4:
                burst(strength)
        where[:] += speed * s.dt
        speed[:] *= 0.5 ** (s.dt / 0.28)
        life[:] -= s.dt
        alive = life > 0
        spots = where[alive].astype(int) % NUM_PIXELS
        levels = np.clip(life[alive] * 2, 0, 1)[:, None]
        rgb = tint(np.full(NUM_PIXELS, 0.015 + 0.1 * s.low), a)
        np.add.at(rgb, spots, levels * b)
        np.add.at(rgb, spots, levels ** 3 * c)
        return rgb
    return draw


def checker_flip(a, b, c):
    """The whole house becomes a checkerboard that flips on every beat, its squares changing size each bar."""
    sizes = random.choice(((10, 20, 40, 20), (25, 50, 25, 100), (20, 40, 80, 40)))

    def draw(s):
        size = sizes[s.bar % len(sizes)]
        odd = ((x // size) + s.count) % 2
        kick = 0.35 + 0.65 * (1 - s.phase) ** 2
        level = kick * (0.35 + 0.65 * s.loud)
        accent = (s.count % BEATS_PER_BAR == 0) * (1 - s.phase) ** 3
        return tint(odd * level, a) + tint((1 - odd) * level, b) + tint(odd * accent * 0.7, c)
    return draw


def sector_strobe(a, b, c):
    """Chunks of the house slam on twice a beat, somewhere new each time."""
    glow = np.zeros(NUM_PIXELS)
    tints = np.tile(a, (NUM_PIXELS, 1))
    last = [-1]

    def draw(s):
        tick = s.count * 2 + int(s.phase * 2)
        if tick != last[0]:
            last[0] = tick
            for _ in range(3):
                spots = (random.randrange(NUM_PIXELS) + np.arange(random.randint(18, 60))) % NUM_PIXELS
                glow[spots] = 0.5 + 0.5 * s.loud
                tints[spots] = c if tick % 8 == 0 else (a if tick % 2 else b)
        glow[:] *= 0.5 ** (s.dt / 0.08)
        return glow[:, None] * tints + tint(np.full(NUM_PIXELS, 0.01 + 0.07 * s.low), a)
    return draw


def plasma_storm(a, b, c):
    """Boiling plasma racing with the bass, its colors turning inside out on each bar."""
    flow = [random.uniform(0, 9)]
    scale = random.uniform(0.7, 1.4)

    def draw(s):
        flow[0] += s.dt * (0.5 + 4.5 * s.low) + (0.25 if s.beat else 0)
        boil = np.sin(x * 0.07 * scale + flow[0]) + np.sin(x * 0.023 * scale - flow[0] * 1.3) + np.sin(x * 0.13 * scale + flow[0] * 0.5)
        if s.bar % 2:
            boil = -boil
        level = 0.3 + 0.7 * s.loud
        return tint(np.clip(boil, 0, 1) * level, a) + tint(np.clip(-boil, 0, 1) * level, b) + tint(np.clip(np.abs(boil) - 1.7, 0, 1) * (0.5 + 0.5 * s.high), c)
    return draw


def bouncing_skulls(a, b, c):
    """Skulls bounce back and forth at three speeds, each hitting the wall exactly on the beat."""
    count = random.choice((3, 4, 5))
    width = NUM_PIXELS / count
    u = x % width
    trail = np.zeros((3, NUM_PIXELS))
    rates = (0.25, 0.5, 1.0)
    colors = (a, b, c)

    def draw(s):
        rgb = np.zeros((NUM_PIXELS, 3))
        time_in = s.count + s.phase
        trail[:] *= 0.5 ** (s.dt / 0.1)
        for i, rate in enumerate(rates):
            where = abs((time_in * rate) % 2 - 1) * (width - 2) + 1
            trail[i] = np.maximum(trail[i], np.exp(-((u - where) / 1.8) ** 2))
            rgb += tint(trail[i] * (0.35 + 0.65 * s.loud), colors[i])
        rgb += tint(np.exp(-(np.minimum(u, width - u) / 3) ** 2) * (1 - s.phase) ** 4 * 0.7, c)
        return rgb
    return draw


def watching_eye(a, b, c):
    """Giant eyes look side to side in time with the music, widening with the bass and blinking on the bar."""
    count = random.choice((3, 4, 5))
    d = panels(count)
    width = NUM_PIXELS / count
    u = x % width - width / 2

    def draw(s):
        look = math.sin(math.pi * (s.count + s.phase) / 2) * width * 0.25
        open_up = 0.0 if s.downbeat or (s.count % BEATS_PER_BAR == 0 and s.phase < 0.12) else 1.0
        white = np.clip((width * 0.42) * open_up - d, 0, 1) * (0.05 + 0.25 * s.low)
        iris = np.exp(-((u - look) / (3 + 7 * s.low)) ** 2) * open_up
        pupil = np.exp(-((u - look) / 1.5) ** 2) * open_up
        return tint(white, a) + tint(iris * (0.5 + 0.5 * s.loud), b) + tint(pupil, c)
    return draw


def sound_river(a, b, c):
    """The sound itself pours outward along the lights: bass, melody and treble each in its own color."""
    d = panels(random.choice((2, 3, 4, 6))).astype(int)
    river = np.zeros((int(d.max()) + 2, 3))
    carry = [0.0]

    def draw(s):
        carry[0] += s.dt * (70 + 120 * s.loud)
        steps = min(int(carry[0]), 12)
        carry[0] -= int(carry[0])
        if steps:
            river[steps:] = river[:-steps]
            river[:steps] = a * s.low ** 2 + b * s.mid ** 2 * 0.8 + c * s.high ** 3 * 0.8
        return river[d]
    return draw


def rising_tide(a, b, c):
    """Each bar the color climbs outward, pumping on every beat, until the next bar dumps it and starts over."""
    d = panels(random.choice((2, 3, 4, 6)))
    reach = d.max()

    def draw(s):
        into = (s.count % BEATS_PER_BAR + s.phase) / BEATS_PER_BAR
        front = reach * into ** 1.4
        body = np.clip(front - d, 0, 1)
        pump = 0.3 + 0.5 * (1 - s.phase) ** 2 + 0.2 * s.low
        tip = np.exp(-((d - front) / 2) ** 2)
        one, two = (a, b) if s.bar % 2 else (b, a)
        return tint(body * pump * (0.3 + 0.7 * d / reach), one) + tint(tip, c) + tint((1 - body) * (0.01 + 0.08 * s.low), two)
    return draw


def glitch_signal(a, b, c):
    """A cursed signal: blocks of color scramble on every note and slide along with each beat."""
    cells = random.choice((32, 40, 50))
    size = NUM_PIXELS // cells
    which = x // size
    level = np.zeros(cells)
    kinds = np.random.randint(0, 3, cells)
    colors = np.array([a, b, c])
    shift = [0]

    def draw(s):
        for strength in s.hits:
            spots = np.random.randint(0, cells, 3 + int(strength * 7))
            level[spots] = 0.4 + 0.6 * strength
            kinds[spots] = np.random.randint(0, 3, len(spots))
        if s.beat:
            shift[0] += random.choice((-3, -2, 2, 3))
        level[:] *= 0.5 ** (s.dt / 0.2)
        spot = (which + shift[0]) % cells
        rgb = level[spot][:, None] * colors[kinds[spot]]
        return rgb + tint((np.random.random(NUM_PIXELS) < 0.05 * s.high) * s.high, c)
    return draw


def barbed_wire(a, b, c):
    """Two strands of barbs slide against each other a step at a time, sparking on the hits."""
    period = random.choice((12, 16, 20, 25))
    spark = [0.0]

    def draw(s):
        if s.hits:
            spark[0] = max(spark[0], max(s.hits))
        spark[0] *= 0.5 ** (s.dt / 0.1)
        step = (s.count + min(1.0, s.phase * 3)) * period / 2
        one = np.abs(((x - step) / period) % 1 * 2 - 1) ** 5
        two = np.abs(((x + step) / period) % 1 * 2 - 1) ** 5
        return tint(one * (0.3 + 0.6 * s.loud), a) + tint(two * (0.2 + 0.7 * s.mid), b) + tint((one + two) * spark[0] * 0.7, c)
    return draw


def blood_rain(a, b, c):
    """Rain pours along the lights, harder as the music gets louder, and the bass splashes through it."""
    most = 70
    where = np.random.uniform(0, NUM_PIXELS, most)
    speed = np.random.uniform(70, 190, most)
    way = random.choice((-1, 1))
    splash = np.zeros(NUM_PIXELS)

    def draw(s):
        where[:] += way * speed * s.dt * (0.6 + 1.2 * s.low)
        falling = int(most * (0.2 + 0.8 * s.loud))
        rgb = np.zeros((NUM_PIXELS, 3))
        for back, level in ((0, 1.0), (1, 0.6), (2, 0.35), (3, 0.15)):
            np.add.at(rgb, (where[:falling] - way * back).astype(int) % NUM_PIXELS, a * level)
        for strength in s.kicks:
            if strength > 0.2:
                splash[(random.randrange(NUM_PIXELS) + np.arange(random.randint(10, 30))) % NUM_PIXELS] = strength
        splash[:] *= 0.5 ** (s.dt / 0.1)
        return rgb + tint(splash, c) + tint(np.full(NUM_PIXELS, 0.01 + 0.08 * s.low), b)
    return draw


def static_swarm(a, b, c):
    """A crackling swarm thickens wherever its part of the sound is loud, and changes color with the beat."""
    count = 8
    which = (x // (NUM_PIXELS / count)).astype(int)
    order = np.random.permutation(count)
    d = panels(count)
    reach = d.max()
    colors = [a, b]

    def draw(s):
        thick = (s.bands[order] ** 2)[which] * (1.1 - d / reach)
        specks = np.random.random(NUM_PIXELS) < thick * 0.7
        return tint(specks * (0.45 + 0.55 * s.loud), colors[s.count % 2]) + tint(specks * (np.random.random(NUM_PIXELS) < 0.12), c) + tint(
            np.full(NUM_PIXELS, 0.01 + 0.05 * s.low), a)
    return draw


ACTS = {
    0: [fog_and_sparks, eyes_in_the_dark, creeping_tendrils, bleeding_veins, moonrise, wandering_wisps, candle_row, plucked_strings,
        heartbeat_monitor, passing_ghosts, dripping_ooze, crawling_cracks],
    1: [creeping_tendrils, eyes_in_the_dark, bleeding_veins, graveyard_march, reapers_scythe, witch_fire, jack_o_lanterns,
        moonrise, wandering_wisps, candle_row, plucked_strings, heartbeat_monitor, passing_ghosts, dripping_ooze, crawling_cracks,
        skeleton_ribs, pendulum, cauldron_bubbles, haunted_piano, falling_souls, haunted_windows, storm_clouds],
    2: [graveyard_march, spectrum_tombstones, witch_fire, serpents, kaleidoscope, reapers_scythe, shockwaves,
        skeleton_ribs, bat_flock, pendulum, cauldron_bubbles, vu_ladder, haunted_piano, braided_serpents, falling_souls, snapping_jaws,
        ghost_train, haunted_windows, storm_clouds, sound_river, rising_tide, barbed_wire, static_swarm, watching_eye, bouncing_skulls],
    3: [shockwaves, bone_chase, lightning_riot, serpents, kaleidoscope, spectrum_tombstones, witch_fire,
        bat_flock, vu_ladder, braided_serpents, snapping_jaws, ghost_train, storm_clouds,
        implosion, buzzsaw, soul_burst, checker_flip, sector_strobe, plasma_storm, bouncing_skulls, watching_eye, sound_river,
        rising_tide, glitch_signal, barbed_wire, blood_rain, static_swarm],
}
