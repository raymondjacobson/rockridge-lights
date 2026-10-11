"""Halloween with sound: spooky soundscapes, and every so often a song.

Each soundscape (owls, a thunderstorm, wolves...) has its own scene that
reacts to the audio, and songs get one of the music visualizers. Colors are
mostly dark purple and red, with orange for light and warmth and green only
for the occasional wisp or vine.

Sounds come from sounds/ambience and sounds/music (see audio.py). Run it
standalone with `nohup python halloween_audio.py &`, or from the control panel.
"""
import math
import random

import numpy as np

import audio
import lights
from halloween26 import frames, show, tint, distance, x
from lights import NUM_PIXELS, rotate

SONG_EVERY = 4  # soundscapes between songs

RED = np.array([1.0, 0.0, 0.0])
ORANGE = np.array([1.0, 0.3, 0.0])
PURPLE = np.array([0.5, 0.0, 1.0])
GREEN = np.array([0.35, 1.0, 0.0])
LIGHTNING = np.array([0.8, 0.7, 1.0])


def play_scene(track, draw, minimum=20):
    """Play `track`, showing draw(playback, t, dt) every frame until it ends.

    A track shorter than `minimum` seconds plays a few times, with a pause between.
    """
    if track is None:
        quiet_glow()
        return
    plays, gap = 1, 0.5
    if track.duration < minimum:
        gap = 4
        plays = math.ceil(minimum / (track.duration + gap))
    playback = None
    try:
        for t, dt, fade in frames(plays * (track.duration + gap)):
            if playback is None or (t >= playback.at + track.duration + gap):
                if playback:
                    playback.__exit__()
                playback = audio.play(track)
                playback.at = t
            show(draw(playback, t, dt), fade)
    finally:
        if playback:
            playback.__exit__()


def quiet_glow(seconds=30):
    """No sound: a slow red and purple glow, used when there's nothing to play."""
    for t, dt, fade in frames(seconds):
        swell = 0.5 + 0.5 * np.sin(x * 0.04 - t * 0.3)
        show(tint(0.04 + 0.12 * swell, RED) + tint(0.05 * (1 - swell), PURPLE), fade)


# Soundscapes


def owl_watch(track=None):
    """Owls hoot in a purple night; each hoot opens a pair of amber eyes that blink and fade."""
    track = track or audio.pick("ambience", "owl")
    if track is None:
        return quiet_glow()
    hoots = audio.Cues(audio.rises(track.features["loud"], gap=1.5))
    eyes = []  # [position, age, strength]

    def draw(playback, t, dt):
        for _ in hoots.due(playback.t):
            if len(eyes) < 6:
                eyes.append([random.randrange(NUM_PIXELS), 0.0, random.uniform(0.7, 1.0)])
        rgb = tint(0.025 + 0.02 * np.sin(x * 0.03 + t * 0.2), PURPLE)
        hoot = playback.loudness()
        for eye in eyes:
            eye[1] += dt
            position, age, strength = eye
            level = strength * min(1.0, age / 0.5, max(0.0, (6 - age) / 1.5))
            if 2.5 < age % 3.2 < 2.65:  # blink
                level *= 0.1
            for offset in (0, 1, 4, 5):
                rgb[(position + offset) % NUM_PIXELS] += ORANGE * level * (0.7 + 0.3 * hoot)
        eyes[:] = [e for e in eyes if e[1] < 6]
        return rgb

    play_scene(track, draw)


def thunderstorm(track=None):
    """Purple clouds churn with the rumble; lightning strikes a moment before each thunderclap."""
    track = track or audio.pick("ambience", "thunder", "storm")
    if track is None:
        return quiet_glow()
    # Thunderclaps are big jumps in the bass; the light comes a moment before the sound.
    claps = audio.rises(track.features["bands"][:, :3].mean(axis=1), high=0.65, gap=6, smooth=0.25)
    strikes = [when - random.uniform(0.3, 1.0) for when in claps]
    flashes = []  # [center, width, start]

    def draw(playback, t, dt):
        now = playback.t
        while strikes and strikes[0] <= now:
            strikes.pop(0)
            flashes.append([random.uniform(0, NUM_PIXELS), random.uniform(40, 120), now])
        rumble = playback.level("low")
        clouds = (0.5 + 0.5 * np.sin(x * 0.05 - t * 0.4)) * (0.5 + 0.5 * np.sin(x * 0.013 + t * 0.15))
        rgb = tint(0.02 + 0.12 * rumble * clouds, PURPLE)
        rain = np.random.random(NUM_PIXELS) < 0.015 * playback.level("high")
        rgb += tint(rain * 0.12, LIGHTNING)
        for center, width, start in flashes:
            age = now - start
            flicker = sum(a * math.exp(-((age - p) / 0.05) ** 2) for p, a in ((0, 0.85), (0.16, 0.5), (0.34, 0.7)))
            shape = np.exp(-(distance(x, center) / width) ** 2)
            rgb += tint(shape * flicker, LIGHTNING) + tint(shape * 0.3 * math.exp(-age / 0.7), PURPLE)
        flashes[:] = [f for f in flashes if now - f[2] < 3]
        return rgb

    play_scene(track, draw)


def wolf_moon(track=None):
    """A harvest moon rises over the house and swells as the wolves howl."""
    center = random.uniform(0, NUM_PIXELS)
    howl = [0.0]

    def draw(playback, t, dt):
        loud = playback.loudness()
        howl[0] += (loud - howl[0]) * min(1.0, dt * (3 if loud > howl[0] else 0.8))
        radius = 10 + 45 * howl[0]
        d = distance(x, center)
        moon = np.clip(1 - d / radius, 0, 1) ** 0.6
        halo = np.exp(-d / (radius * 1.5)) * 0.12 * howl[0]
        return (tint(0.02 + 0.01 * np.sin(x * 0.1 + t), PURPLE)
                + tint(moon * (0.15 + 0.7 * howl[0]), ORANGE) + tint(halo, RED))

    play_scene(track or audio.pick("ambience", "wolf", "wolves"), draw)


def ravens(track=None):
    """Lanterns flicker orange; with each caw a raven's shadow sweeps across them."""
    track = track or audio.pick("ambience", "crow", "raven")
    if track is None:
        return quiet_glow()
    caws = audio.Cues(audio.rises(track.features["loud"], high=0.55, low=0.3, gap=0.4))
    lanterns = (x % 25) < 5
    flame = np.random.uniform(0.6, 1.0, NUM_PIXELS)
    shadows = []  # [position, direction, speed, age]

    def draw(playback, t, dt):
        for _ in caws.due(playback.t):
            if len(shadows) < 8:
                shadows.append([random.uniform(0, NUM_PIXELS), random.choice((-1, 1)),
                                random.uniform(40, 90), 0.0])
        flame[:] += (np.random.uniform(0.55, 1.0, NUM_PIXELS) - flame) * min(1.0, dt * 6)
        light = np.where(lanterns, 0.35 * flame, 0.015)
        wings = np.zeros(NUM_PIXELS)
        for shadow in shadows:
            shadow[0] = (shadow[0] + shadow[1] * shadow[2] * dt) % NUM_PIXELS
            shadow[3] += dt
            d = distance(x, shadow[0])
            light *= 1 - 0.95 * np.exp(-(d / 7) ** 2)
            wings += 0.12 * abs(math.sin(shadow[3] * 10)) * np.exp(-((d - 8) / 3) ** 2)
        shadows[:] = [s for s in shadows if s[3] < 4]
        return tint(light, ORANGE) + tint(wings, PURPLE)

    play_scene(track, draw)


def creaking_door(track=None):
    """Somewhere a door creaks open, spilling candlelight; it swings shut when the creaking stops."""
    door = random.uniform(0, NUM_PIXELS)
    opening = [0.0]

    def draw(playback, t, dt):
        target = 40 * playback.loudness()
        rate = 1.5 if target > opening[0] else 0.4
        opening[0] += (target - opening[0]) * min(1.0, dt * rate)
        d = distance(x, door)
        beam = np.clip(opening[0] / 2 - d + 1, 0, 1)
        spill = np.exp(-d / (opening[0] + 4)) * 0.08
        flicker = 0.85 + 0.15 * math.sin(t * 9) * math.sin(t * 5.3)
        return tint(np.full(NUM_PIXELS, 0.015), PURPLE) + tint(beam * 0.6 * flicker + spill, ORANGE)

    play_scene(track or audio.pick("ambience", "door", "creak"), draw)


def will_o_wisps(track=None):
    """Green will-o'-the-wisps drift around the house, hurried along by the gusting wind."""
    wisps = [[random.uniform(0, NUM_PIXELS), random.choice((-1, 1)), random.uniform(0, 6)]
             for _ in range(4)]

    def draw(playback, t, dt):
        wind = playback.loudness()
        rgb = tint(0.02 + 0.06 * wind * (0.5 + 0.5 * np.sin(x * 0.02 - t * (0.5 + wind))), PURPLE)
        for wisp in wisps:
            wisp[0] = (wisp[0] + wisp[1] * (3 + 35 * wind) * dt) % NUM_PIXELS
            level = 0.3 + 0.2 * math.sin(t * 1.7 + wisp[2])
            rgb += tint(level * np.exp(-(distance(x, wisp[0]) / 3.5) ** 2), GREEN)
        return rgb

    play_scene(track or audio.pick("ambience", "wind"), draw)


def midnight_bell(track=None):
    """Each toll of the bell sends a slow purple ring across the house, over dim red embers."""
    center = random.uniform(0, NUM_PIXELS)
    rings = []  # [start, strength]
    embers = np.random.uniform(0, 2 * math.pi, NUM_PIXELS)

    def draw(playback, t, dt):
        now = playback.t
        for strength in playback.new_onsets():
            if strength > 0.25 and (not rings or now - rings[-1][0] > 1.5):
                rings.append([now, strength])
        rgb = tint(0.03 + 0.02 * np.sin(embers + t * 0.7), RED)
        d = distance(x, center)
        for start, strength in rings:
            age = now - start
            ring = np.exp(-((d - age * 40) / 6) ** 2) * (0.3 + 0.5 * strength) * math.exp(-age / 3)
            rgb += tint(ring, PURPLE)
        rings[:] = [r for r in rings if now - r[0] < 8]
        return rgb

    play_scene(track or audio.pick("ambience", "bell", "toll", "chime"), draw)


def haunted_glow(track=None):
    """Any other sound: red and purple swells that breathe with its loudness."""
    level = [0.0]

    def draw(playback, t, dt):
        level[0] += (playback.loudness() - level[0]) * min(1.0, dt * 2)
        swell = 0.5 + 0.5 * np.sin(x * 0.03 - t * 0.4)
        return tint((0.04 + 0.4 * level[0]) * swell, RED) + tint(0.05 * (1 - swell), PURPLE)

    play_scene(track or audio.pick("ambience"), draw)


SOUNDSCAPES = [owl_watch, thunderstorm, wolf_moon, ravens, creaking_door, will_o_wisps, midnight_bell]
KEYWORDS = [
    (("owl",), owl_watch),
    (("thunder", "storm", "lightning"), thunderstorm),
    (("wolf", "wolves"), wolf_moon),
    (("crow", "raven"), ravens),
    (("door", "creak"), creaking_door),
    (("wind",), will_o_wisps),
    (("bell", "toll", "chime"), midnight_bell),
]


def scene_for(track):
    for words, scene in KEYWORDS:
        if track.has_word(*words):
            return scene
    return haunted_glow


# Music


def pumpkin_patch(track=None):
    """Jack-o'-lanterns glow with the bass and flare on the hits, with green vines between them."""
    size = 20
    pumpkin_of = x // size
    spot = x % size
    face = np.where((spot >= 4) & (spot < 17), 1 - np.abs(spot - 10) / 10, 0)
    vine = (spot < 2).astype(float)
    count = NUM_PIXELS // size
    flare = np.zeros(count)
    flame = np.ones(count)

    def draw(playback, t, dt):
        for strength in playback.new_onsets():
            if strength > 0.25:
                flare[random.randrange(count)] = strength
        flare[:] *= 0.5 ** (dt / 0.25)
        flame[:] += (np.random.uniform(0.75, 1.0, count) - flame) * min(1.0, dt * 8)
        level = (0.1 + 0.45 * playback.level("low") + 0.5 * flare) * flame
        return tint(face * level[pumpkin_of], ORANGE) + tint(vine * (0.03 + 0.08 * playback.loudness()), GREEN)

    play_scene(track or audio.pick("music"), draw)


def spectrum_tombstones(track=None):
    """Eight glowing columns rise and fall with the music, purple bass through red to orange treble."""
    bars = 8
    spacing = NUM_PIXELS / bars
    centers = np.arange(bars) * spacing + spacing / 2
    colors = [PURPLE * (1 - f) + RED * f if f < 1 else RED * (2 - f) + ORANGE * (f - 1)
              for f in np.linspace(0, 2, bars)]
    heights = np.zeros(bars)
    caps = np.zeros(bars)

    def draw(playback, t, dt):
        bands = playback.bands()
        heights[:] = np.maximum(bands, heights * 0.5 ** (dt / 0.15))
        caps[:] = np.maximum(heights, caps - dt * 0.6)
        rgb = tint(np.full(NUM_PIXELS, 0.015), PURPLE)
        reach = spacing / 2 - 3
        for b in range(bars):
            d = distance(x, centers[b])
            column = np.clip(heights[b] * reach - d + 1, 0, 1) * (0.25 + 0.55 * (1 - d / reach))
            cap = np.exp(-((d - caps[b] * reach) / 0.8) ** 2) * 0.6 * (caps[b] > 0.05)
            rgb += np.clip(column + cap, 0, 1)[:, None] * colors[b]
        return rgb

    play_scene(track or audio.pick("music"), draw)


def dance_of_the_dead(track=None):
    """Every beat sends a pulse racing both ways around the house: red, orange, purple, and now and then green."""
    pulses = []  # [origin, start, color, strength]
    count = [0]

    def draw(playback, t, dt):
        now = playback.t
        for strength in playback.new_onsets():
            if strength > 0.3 and (not pulses or now - pulses[-1][1] > 0.2):
                count[0] += 1
                color = GREEN if count[0] % 12 == 0 else (RED, ORANGE, PURPLE)[count[0] % 3]
                pulses.append([random.uniform(0, NUM_PIXELS), now, color, strength])
        rgb = tint(np.full(NUM_PIXELS, 0.02 + 0.08 * playback.loudness()), PURPLE)
        for origin, start, color, strength in pulses:
            age = now - start
            wave = np.exp(-((distance(x, origin) - age * 110) / 5) ** 2)
            rgb += tint(wave * (0.3 + 0.6 * strength) * math.exp(-age / 1.2), color)
        pulses[:] = [p for p in pulses if now - p[1] < 2.5]
        return rgb

    play_scene(track or audio.pick("music"), draw)


VISUALIZERS = [pumpkin_patch, spectrum_tombstones, dance_of_the_dead]

recent = []  # names of recently played tracks, to avoid repeats


def fits(track):
    """Whether the track can finish before the scheduled off time."""
    return not lights.schedule_on or lights.is_show_time(track.duration)


def halloween_night():
    """The full show: a few soundscapes, then a song, over and over."""
    for _ in range(SONG_EVERY):
        track = audio.pick("ambience", avoid=recent[-4:])
        if track is None or not fits(track):
            return quiet_glow()
        recent.append(track.name)
        scene_for(track)(track)
    song = audio.pick("music", avoid=recent[-12:])
    if song is not None and fits(song):
        recent.append(song.name)
        random.choice(VISUALIZERS)(song)


if __name__ == "__main__":
    rotate([halloween_night], seconds=1, shuffle=False, scheduled=True)
