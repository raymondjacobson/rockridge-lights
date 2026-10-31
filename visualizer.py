"""The light show for songs: a whole sequence worked out from the music before it starts.

plan_song() finds the song's beats and bars and splits it into sections where
the sound changes. Each section gets an act (fire, serpents, shockwaves...)
that suits how hard the music is going and a palette of its own; a new act
bursts outward from around the house over the old one, on a bar line. Quiet
parts stay dark and creeping, loud parts get fast and bright.

The acts themselves are in song_acts.py.
"""
import json
import math
import random
from types import SimpleNamespace

import numpy as np

import audio
from halloween26 import distance, tint, x
from lights import NUM_PIXELS
from song_acts import ACTS, PALE, PALETTES, panels

MIN_SECTION = 8  # seconds
MAX_SECTION = 24
BEATS_PER_BAR = 4
FLASH_GAP = 0.5  # seconds between whole-house flashes: never more than two a second, for anyone watching
MOST_LIGHT = 0.5  # the average level a frame may reach, to go easy on the power supply
TIER_GAIN = (0.6, 0.8, 0.95, 1.0)

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


def glitter(section):
    """The top of the music glitters over everything."""
    def draw(s):
        rgb = np.zeros((NUM_PIXELS, 3))
        count = int(NUM_PIXELS * 0.03 * max(0, s.high - 0.35))
        if count:
            rgb[np.random.randint(0, NUM_PIXELS, count)] += section.palette[2] * s.high
        return rgb
    return draw


def bar_comets(section):
    """On each bar a bright pair of comets runs out from a new place."""
    start = [-9.0, 0.0]

    def draw(s):
        if s.downbeat:
            start[:] = [s.now, random.uniform(0, NUM_PIXELS)]
        age = s.now - start[0]
        d = distance(x, start[1])
        return tint(np.exp(-((d - age * 150) / 3) ** 2) * math.exp(-age / 0.6) * (0.5 + 0.5 * s.loud), section.palette[2])
    return draw


def kick_halves(section):
    """The bass lights alternate stretches of the house."""
    stretches = random.choice((2, 4))
    odd = ((x // (NUM_PIXELS / (stretches * 2))) % 2).astype(float)
    glow = [0.0, 0.0]
    turn = [0]

    def draw(s):
        for strength in s.kicks:
            if strength > 0.2:
                turn[0] ^= 1
                glow[turn[0]] = 0.15 + 0.25 * strength
        glow[0] *= 0.5 ** (s.dt / 0.1)
        glow[1] *= 0.5 ** (s.dt / 0.1)
        return tint(odd * glow[0] + (1 - odd) * glow[1], section.palette[1])
    return draw


def note_sparks(section):
    """Each note leaves a few sparks."""
    sparks = np.zeros(NUM_PIXELS)

    def draw(s):
        for strength in s.hits:
            sparks[np.random.randint(0, NUM_PIXELS, 2 + int(strength * 5))] = 0.4 + 0.6 * strength
        sparks[:] *= 0.5 ** (s.dt / 0.15)
        return tint(sparks, section.palette[2])
    return draw


OVERLAYS = [glitter, glitter, bar_comets, kick_halves, note_sparks, None]
DUET_ODDS = 0.3  # how often a section splits the house between two acts
RECENT_ACTS = audio.CACHE / "recent_song_acts.json"


def recently_played():
    try:
        return json.loads(RECENT_ACTS.read_text())
    except (OSError, ValueError):
        return []


def choose_acts(sections):
    """An act, a palette and maybe a partner and an overlay per section, favoring what hasn't played lately, even in earlier songs."""
    recent = recently_played()
    colors = []

    def pick_act(tier, other=None):
        def last_played(act):
            name = act.__name__
            return (len(recent) - recent[::-1].index(name)) if name in recent else -random.random()
        fresh = sorted((a for a in ACTS[tier] if a is not other), key=last_played)[:4]
        act = random.choice(fresh)
        recent.append(act.__name__)
        return act

    def pick_palette():
        palette = random.choice([p for p in PALETTES if not any(p is q for q in colors[-4:])])
        colors.append(palette)
        return palette

    for section in sections:
        section.act = pick_act(section.tier)
        section.palette = pick_palette()
        section.partner = section.partner_palette = None
        if section.tier >= 1 and random.random() < DUET_ODDS:
            section.partner = pick_act(section.tier, section.act)
            section.partner_palette = pick_palette()
        section.overlay = random.choice(OVERLAYS) if section.tier >= 1 else None
    try:
        RECENT_ACTS.parent.mkdir(parents=True, exist_ok=True)
        RECENT_ACTS.write_text(json.dumps(recent[-80:]))
    except OSError as e:
        print("couldn't remember the acts:", e, flush=True)


def stage(section):
    """The draw(s) for a section: its act, shared with a partner if it has one, plus its overlay."""
    main = section.act(*section.palette)
    partner = section.partner and section.partner(*section.partner_palette)
    overlay = section.overlay and section.overlay(section)
    stretches = random.choice((2, 4, 8))
    odd = ((x // (NUM_PIXELS / (stretches * 2))) % 2 == 1)[:, None]

    def draw(s):
        rgb = main(s)
        if partner:
            other = partner(s)
            rgb = np.where(odd != (s.bar // 4 % 2 == 1), rgb, other)  # they swap sides every four bars
        return rgb + overlay(s) if overlay else rgb
    return draw


def sequence(track):
    """A draw(playback, t, dt) for play_scene: the whole song's light show."""
    beats, offset, sections = plan_song(track)
    choose_acts(sections)
    print("{}: {} beats, {} sections: {}".format(track.name, len(beats), len(sections), ", ".join(
        "{:.0f}s {}{}".format(p.start, p.act.__name__, " + " + p.partner.__name__ if p.partner else "") for p in sections)), flush=True)
    starts = np.array([p.start for p in sections])
    cues = audio.Cues(beats.tolist())
    s = SimpleNamespace(now=0.0, dt=0.0, low=0.0, mid=0.0, high=0.0, loud=0.0, bands=np.zeros(8), hits=[], kicks=[], beat=False,
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
        s.kicks = playback.new_onsets(low=True)
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
            state.draw = stage(section)
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

        state.gate += (min(1.0, s.loud / 0.12) - state.gate) * min(1.0, dt * 10)  # silence goes dark
        rgb = rgb * (0.2 + 0.8 * state.gate)
        light = float(np.clip(rgb, 0, 1).mean())
        return rgb * (MOST_LIGHT / light) if light > MOST_LIGHT else rgb
    return draw
