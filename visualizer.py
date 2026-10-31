"""The light show for songs: a whole sequence worked out from the music before it starts.

plan_song() finds the song's beats and bars and splits it into sections where
the sound changes. Each section gets an act (fire, serpents, shockwaves...)
that suits how hard the music is going and a palette of its own; a new act
bursts outward from around the house over the old one, on a bar line. Quiet
parts stay dark and creeping, loud parts get fast and bright.

Every act is act(a, b, c) with three colors, returning draw(s), which takes
the moment `s` from sequence() and returns an (N, 3) array of 0..1 colors.
"""
import math
import random
from types import SimpleNamespace

import numpy as np

import audio
from halloween26 import tint, distance, x
from lights import NUM_PIXELS

MIN_SECTION = 8  # seconds
MAX_SECTION = 24
BEATS_PER_BAR = 4
FLASH_GAP = 0.5  # seconds between whole-house flashes: never more than two a second, for anyone watching
MOST_LIGHT = 0.5  # the average level a frame may reach, to go easy on the power supply
TIER_GAIN = (0.6, 0.8, 0.95, 1.0)

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
]


def panels(count, shift=0):
    """How far each light is from the center of its stretch of house, with `count` stretches."""
    width = NUM_PIXELS / count
    return np.abs((x + shift) % width - width / 2)


# Finding the shape of the song


def onset_envelope(features):
    frames = len(features["loud"])
    envelope = np.zeros(frames)
    for prefix, weight in (("onset_", 1.0), ("low_onset_", 1.5)):
        spots = np.clip((features[prefix + "times"] * audio.RATE).astype(int), 0, frames - 1)
        np.add.at(envelope, spots, features[prefix + "strengths"] * weight)
    return np.convolve(envelope, [0.25, 0.5, 1, 0.5, 0.25], mode="same")


def find_beats(features):
    """Beat times: a steady pulse at the song's tempo that bends to land on what's actually played."""
    envelope = onset_envelope(features)
    power = np.abs(np.fft.rfft(envelope, len(envelope) * 2)) ** 2
    repeats = np.fft.irfft(power)
    lags = np.arange(int(audio.RATE * 60 / 190), int(audio.RATE * 60 / 65))
    if len(envelope) <= lags[-1] * 2:
        return np.array([])
    favor = np.exp(-0.5 * (np.log2(lags / (audio.RATE * 60 / 115)) / 0.9) ** 2)
    period = lags[np.argmax(repeats[lags] * favor)]

    gaps = np.arange(period // 2, period * 2 + 1)
    penalty = -4.0 * envelope.mean() * np.log(gaps / period) ** 2 * period / 4
    score = envelope.copy()
    came_from = np.full(len(envelope), -1)
    for i in range(gaps[-1], len(envelope)):
        before = score[i - gaps] + penalty
        best = int(before.argmax())
        if before[best] > 0:
            score[i] += before[best]
            came_from[i] = i - gaps[best]
    i = len(envelope) - period + int(score[-period:].argmax())
    beats = []
    while i >= 0:
        beats.append(i)
        i = came_from[i]
    return np.array(beats[::-1]) / audio.RATE


def plan_song(track):
    """(beats, downbeat offset, sections), with each section's start, end, tier 0-3 and whether the music jumped up."""
    features = track.features
    duration = float(track.duration)
    beats = find_beats(features)
    if len(beats) < BEATS_PER_BAR * 4:  # nothing to go on: an even pulse
        beats = np.arange(0, duration, 0.5)

    low = onset_envelope({**features, "onset_strengths": features["onset_strengths"] * 0})
    frames = np.clip((beats * audio.RATE).astype(int), 0, len(low) - 1)
    offset = int(np.argmax([low[frames[o::BEATS_PER_BAR]].sum() for o in range(BEATS_PER_BAR)]))
    bars = beats[offset::BEATS_PER_BAR]

    # Sections start at the bars where the sound before and after differ the most.
    sound = np.column_stack([features["bands"], features["loud"]])
    spots = np.clip((bars * audio.RATE).astype(int), 0, len(sound) - 1)
    edges = np.concatenate([[0], spots[1:]])
    per_bar = np.add.reduceat(sound, edges) / np.maximum(1, np.diff(np.append(edges, len(sound))))[:, None]
    change = np.zeros(len(bars))
    for b in range(1, len(bars)):
        change[b] = np.linalg.norm(per_bar[b:b + 4].mean(axis=0) - per_bar[max(0, b - 4):b].mean(axis=0))
    starts = [0.0, duration]
    for b in np.argsort(-change):
        if change[b] > np.median(change) * 1.3 and all(abs(bars[b] - s) >= MIN_SECTION for s in starts):
            starts.append(float(bars[b]))
    starts.sort()
    for left, right in zip(starts[:-1], starts[1:]):  # long stretches still move on
        between = [float(b) for b in bars if left + MIN_SECTION <= b <= right - MIN_SECTION]
        count = int((right - left) // MAX_SECTION)
        for n in range(1, count + 1):
            if between:
                aim = left + (right - left) * n / (count + 1)
                starts.append(min(between, key=lambda b: abs(b - aim)))
    starts = sorted(set(starts))

    onset_times = features["onset_times"]
    energy = []
    for start, end in zip(starts[:-1], starts[1:]):
        part = features["loud"][int(start * audio.RATE):max(int(start * audio.RATE) + 1, int(end * audio.RATE))]
        busy = ((onset_times >= start) & (onset_times < end)).sum() / max(end - start, 1)
        energy.append(0.7 * float(part.mean()) + 0.3 * min(1.0, busy / 6))
    energy = np.array(energy)
    cuts = np.percentile(energy, [25, 50, 75])  # by the song's own range, so every song builds and breaks
    sections = []
    for i, start in enumerate(starts[:-1]):
        jumped = i > 0 and energy[i] - energy[i - 1] > 0.12
        sections.append(SimpleNamespace(start=start, end=starts[i + 1], tier=int(np.digitize(energy[i], cuts)),
                                        jumped=jumped))
    return beats, offset, sections


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


ACTS = {
    0: [fog_and_sparks, eyes_in_the_dark, creeping_tendrils, bleeding_veins],
    1: [creeping_tendrils, eyes_in_the_dark, bleeding_veins, graveyard_march, reapers_scythe, witch_fire, jack_o_lanterns],
    2: [graveyard_march, spectrum_tombstones, witch_fire, serpents, kaleidoscope, reapers_scythe, shockwaves],
    3: [shockwaves, bone_chase, lightning_riot, serpents, kaleidoscope, spectrum_tombstones, witch_fire],
}


def choose_acts(sections):
    """An act and a palette for each section, not repeating one soon."""
    used, colors = [], []
    for section in sections:
        section.act = random.choice([a for a in ACTS[section.tier] if a not in used[-5:]] or ACTS[section.tier])
        section.palette = random.choice([p for p in PALETTES if not any(p is q for q in colors[-2:])])
        used.append(section.act)
        colors.append(section.palette)


def sequence(track):
    """A draw(playback, t, dt) for play_scene: the whole song's light show."""
    beats, offset, sections = plan_song(track)
    choose_acts(sections)
    print("{}: {} beats, {} sections: {}".format(track.name, len(beats), len(sections), ", ".join(
        "{:.0f}s {}".format(p.start, p.act.__name__) for p in sections)), flush=True)
    starts = np.array([p.start for p in sections])
    cues = audio.Cues(beats.tolist())
    s = SimpleNamespace(now=0.0, dt=0.0, low=0.0, mid=0.0, high=0.0, loud=0.0, bands=np.zeros(8), hits=[], beat=False,
                        downbeat=False, count=0, bar=0, phase=0.0, beat_length=0.5)
    state = SimpleNamespace(section=None, draw=None, old=None, wipe=None, wipe_seconds=1.0, flash=0.0, flash_color=PALE,
                            last_flash=-9.0, gate=0.0)
    wipe_from = panels(4)

    def draw(playback, t, dt):
        now = playback.t
        s.now, s.dt = now, dt
        s.low, s.mid, s.high = playback.level("low"), playback.level("mid"), playback.level("high")
        s.loud = playback.loudness()
        s.bands = playback.bands()
        s.hits = playback.new_onsets()
        due = cues.due(now)
        s.beat = bool(due)
        passed = int(np.searchsorted(beats, now, side="right"))
        s.count = max(0, passed - 1 - offset)
        s.bar = s.count // BEATS_PER_BAR
        s.downbeat = s.beat and passed > offset and (passed - 1 - offset) % BEATS_PER_BAR == 0
        if 0 < passed < len(beats):
            s.beat_length = float(beats[passed] - beats[passed - 1])
            s.phase = min(1.0, (now - beats[passed - 1]) / max(s.beat_length, 0.05))

        section = sections[max(0, int(np.searchsorted(starts, now, side="right")) - 1)]
        if section is not state.section:
            state.old, state.wipe = state.draw, now
            state.draw = section.act(*section.palette)
            state.wipe_seconds = max(0.4, min(1.5, s.beat_length * 2))
            state.section = section
            if section.jumped:
                state.flash = 0.8
                state.flash_color = section.palette[2]
                state.last_flash = now
        rgb = state.draw(s)
        if state.old is not None:
            spread = (now - state.wipe) / state.wipe_seconds
            if spread >= 1:
                state.old = None
            else:
                mask = np.clip((spread * 60 - wipe_from) / 8, 0, 1)[:, None]
                rgb = rgb * mask + state.old(s) * (1 - mask)

        if s.downbeat and section.tier >= 2 and s.bar % 4 == 0 and now - state.last_flash >= FLASH_GAP:
            state.flash = 0.35
            state.flash_color = section.palette[2]
            state.last_flash = now
        state.flash *= 0.5 ** (dt / 0.09)
        rgb = rgb * TIER_GAIN[section.tier] + state.flash * state.flash_color

        if section.tier >= 1 and s.high > 0.35:  # the top of the music glitters over everything
            count = int(NUM_PIXELS * 0.03 * (s.high - 0.35))
            if count:
                rgb[np.random.randint(0, NUM_PIXELS, count)] += section.palette[2] * s.high

        state.gate += (min(1.0, s.loud / 0.12) - state.gate) * min(1.0, dt * 10)  # silence goes dark
        rgb = rgb * (0.2 + 0.8 * state.gate)
        light = float(np.clip(rgb, 0, 1).mean())
        return rgb * (MOST_LIGHT / light) if light > MOST_LIGHT else rgb
    return draw
