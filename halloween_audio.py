"""Halloween with sound: spooky soundscapes, now and then Halloween reds, and every so often a song.

Each soundscape (owls, a thunderstorm, wolves...) has its own scene that
reacts to the audio, and songs get one of the music visualizers. The full
show changes about every minute; a song plays to its end. Colors are mostly
dark purple and red, with orange for light and warmth and green only for
the occasional wisp or vine, except where a scene needs its own.

Sounds come from sounds/ambience and sounds/music (see audio.py). Run it
standalone with `nohup python halloween_audio.py &`, or from the control panel.
"""
import math
import random
import time

import numpy as np

import audio
import lights
from halloween26 import PATTERNS, frames, show, tint, distance, x
from lights import NUM_PIXELS, rotate

SCENE_SECONDS = 60  # about how long each scene lasts in the full show
SCENES_BEFORE_REDS = 3  # soundscapes before a Halloween reds pattern
REDS_BEFORE_SONG = 2  # Halloween reds patterns before a song

scene_seconds = None  # how long a scene runs: set during the full show, else it plays its whole track
on_scene = None  # called with each scene's name as the full show gets to it

RED = np.array([1.0, 0.0, 0.0])
ORANGE = np.array([1.0, 0.3, 0.0])
PURPLE = np.array([0.5, 0.0, 1.0])
GREEN = np.array([0.35, 1.0, 0.0])
LIGHTNING = np.array([0.8, 0.7, 1.0])
PALE = np.array([0.55, 0.75, 1.0])
GOLD = np.array([1.0, 0.65, 0.15])
SICKLY = np.array([0.5, 1.0, 0.1])
PINK = np.array([1.0, 0.2, 0.5])


def play_scene(track, draw, minimum=20):
    """Play `track`, showing draw(playback, t, dt) every frame until it ends.

    A track shorter than `minimum` seconds plays a few times, with a pause between.
    """
    if track is None:
        quiet_glow()
        return
    seconds = scene_seconds
    if seconds and track.duration >= seconds * 2 / 3:  # plays once, cut short if it runs long
        minimum = 0
    elif seconds:
        minimum = seconds
    plays, gap = 1, 0.5
    if track.duration < minimum:
        gap = 4
        plays = math.ceil(minimum / (track.duration + gap))
    total = plays * (track.duration + gap)
    if seconds and minimum == 0:
        total = min(total, seconds)
    cut_at = total - audio.FADE_SECONDS if total < track.duration else None
    playback = None
    try:
        for t, dt, fade in frames(total):
            if playback is None or (t >= playback.at + track.duration + gap):
                if playback:
                    playback.__exit__()
                playback = audio.play(track, cut_at)
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


def witch_cackle(track=None):
    """A witch laughs and every cackle throws a jagged green bolt across a purple dusk."""
    bolts = []  # [center, width, start]

    def draw(playback, t, dt):
        now = playback.t
        for strength in playback.new_onsets():
            if strength > 0.25 and len(bolts) < 8:
                bolts.append([random.uniform(0, NUM_PIXELS), random.uniform(15, 60), now])
        rgb = tint(0.03 + 0.05 * playback.loudness() * (0.5 + 0.5 * np.sin(x * 0.04 + t)), PURPLE)
        for center, width, start in bolts:
            jag = 0.6 + 0.4 * np.sin(x * 1.7 + start * 40)
            rgb += tint(np.exp(-(distance(x, center) / width) ** 2) * jag * math.exp(-(now - start) / 0.35), GREEN)
        bolts[:] = [b for b in bolts if now - b[2] < 1.5]
        return rgb

    play_scene(track or audio.pick("ambience", "witch"), draw)


def beast_in_the_dark(track=None):
    """Something big growls: its red eyes open wider with every snarl, deep in the dark."""
    eyes = random.uniform(0, NUM_PIXELS)
    anger = [0.0]

    def draw(playback, t, dt):
        loud = playback.loudness()
        anger[0] += (loud - anger[0]) * min(1.0, dt * (5 if loud > anger[0] else 1))

        d = distance(x, eyes)
        pair = np.exp(-((d - 6) / (1.5 + 2 * anger[0])) ** 2)
        return tint(pair * (0.1 + 0.9 * anger[0]) + 0.03 * anger[0], RED)

    play_scene(track or audio.pick("ambience", "monster"), draw)


def telltale_heart(track=None):
    """The whole house thumps red with a heartbeat that ripples out from under the floorboards."""
    center = random.uniform(0, NUM_PIXELS)
    beats = []  # start times

    def draw(playback, t, dt):
        now = playback.t
        for strength in playback.new_onsets(low=True):
            if strength > 0.2 and (not beats or now - beats[-1] > 0.3):
                beats.append(now)
        d = distance(x, center)
        rgb = tint(np.full(NUM_PIXELS, 0.02), RED)
        for start in beats:
            age = now - start
            rgb += tint(np.exp(-((d - age * 130) / 30) ** 2) * math.exp(-age / 0.7) * 0.8, RED)
        beats[:] = [b for b in beats if now - b < 2.5]
        return rgb

    play_scene(track or audio.pick("ambience", "heartbeat"), draw)


def something_breathing(track=None):
    """Cold blue light swells and sinks all around the house with slow, heavy breaths."""
    breath = [0.0]

    def draw(playback, t, dt):
        breath[0] += (playback.loudness() - breath[0]) * min(1.0, dt * 2.5)
        ribs = 0.6 + 0.4 * np.sin(x * 0.09 - t * 0.5)
        return tint((0.02 + 0.4 * breath[0]) * ribs, PALE * np.array([0.25, 0.5, 1.0]))

    play_scene(track or audio.pick("ambience", "heavy", "breathing"), draw)


def witching_hour(track=None):
    """A clock's hand of orange light jumps around the house with every tick, trailing embers."""
    hand = [random.randrange(NUM_PIXELS)]
    trail = np.zeros(NUM_PIXELS)

    def draw(playback, t, dt):
        for strength in playback.new_onsets():
            if strength > 0.15:
                hand[0] = (hand[0] + NUM_PIXELS // 60) % NUM_PIXELS
                trail[hand[0]] = 1.0
        trail[:] *= 0.5 ** (dt / 1.5)
        return tint(trail * 0.8, ORANGE) + tint(np.exp(-(distance(x, hand[0]) / 2) ** 2), GOLD) + tint(np.full(NUM_PIXELS, 0.012), PURPLE)

    play_scene(track or audio.pick("ambience", "ticking"), draw)


def clock_tower(track=None):
    """The tower strikes the hour: each stroke is a gold flash that rolls away around the house."""
    center = random.uniform(0, NUM_PIXELS)
    strokes = []

    def draw(playback, t, dt):
        now = playback.t
        for strength in playback.new_onsets():
            if strength > 0.25 and (not strokes or now - strokes[-1] > 1.0):
                strokes.append(now)
        d = distance(x, center)
        rgb = tint(np.full(NUM_PIXELS, 0.02 + 0.08 * playback.loudness()), PURPLE)
        for start in strokes:
            age = now - start
            rgb += tint(np.exp(-((d - age * 60) / 14) ** 2) * math.exp(-age / 2) * 0.9, GOLD)
        strokes[:] = [s for s in strokes if now - s < 6]
        return rgb

    play_scene(track or audio.pick("ambience", "strikes"), draw)


def bat_swarm(track=None):
    """Bats flit in crazy zigzags against the last orange of the sunset, quicker as they chirp."""
    bats = np.random.uniform(0, NUM_PIXELS, 24)
    headings = np.random.choice((-1.0, 1.0), 24)

    def draw(playback, t, dt):
        chirp = playback.level("high")
        headings[np.random.random(24) < dt * 2.5] *= -1
        bats[:] = (bats + headings * (15 + 90 * chirp) * dt) % NUM_PIXELS
        sky = 0.06 + 0.05 * np.sin(x * 0.015 + t * 0.1)
        for bat in bats.astype(int):
            sky[(bat + np.arange(-1, 2)) % NUM_PIXELS] = 0
        rgb = tint(sky, ORANGE)
        rgb[bats.astype(int)] += PURPLE * (0.3 + 0.5 * chirp)
        return rgb

    play_scene(track or audio.pick("ambience", "bats"), draw)


def graveyard_crickets(track=None):
    """Crickets sing over the graves while fireflies blink on and off in the grass."""
    glow = np.zeros(NUM_PIXELS)

    def draw(playback, t, dt):
        song = playback.loudness()
        glow[np.random.random(NUM_PIXELS) < dt * (0.1 + 0.8 * song)] = 1.0
        glow[:] *= 0.5 ** (dt / 0.5)
        return tint(glow ** 2 * 0.6, SICKLY) + tint(0.015 + 0.01 * np.sin(x * 0.05), PURPLE)

    play_scene(track or audio.pick("ambience", "crickets"), draw)


def swamp_chorus(track=None):
    """Frogs croak from a murky green swamp, and each croak swells up like a bubble and pops."""
    bubbles = []  # [position, age, strength]

    def draw(playback, t, dt):
        for strength in playback.new_onsets():
            if strength > 0.2 and len(bubbles) < 14:
                bubbles.append([random.uniform(0, NUM_PIXELS), 0.0, strength])
        rgb = tint(0.025 + 0.02 * np.sin(x * 0.07 + t * 0.3), SICKLY)
        for bubble in bubbles:
            bubble[1] += dt
            position, age, strength = bubble
            rgb += tint(np.exp(-(distance(x, position) / (2 + age * 8)) ** 2) * (0.3 + strength) * max(0.0, 1 - age / 0.9), GREEN)
        bubbles[:] = [b for b in bubbles if b[1] < 0.9]
        return rgb

    play_scene(track or audio.pick("ambience", "frogs"), draw)


def serpent(track=None):
    """A long green snake slithers around the house, its tail shaking red when it rattles."""
    head = [random.uniform(0, NUM_PIXELS)]
    length = 70

    def draw(playback, t, dt):
        rattle = playback.loudness()
        head[0] = (head[0] + (8 + 14 * (1 - rattle)) * dt) % NUM_PIXELS
        behind = (head[0] - x) % NUM_PIXELS
        body = (behind < length) * (0.5 + 0.5 * np.sin(behind * 0.5 - t * 3)) * (1 - behind / (length * 1.3))
        tail = (behind >= length - 8) & (behind < length)
        shake = abs(math.sin(t * 45)) * rattle
        return tint(body * 0.55, GREEN) + tint(tail * shake, RED) + tint(np.full(NUM_PIXELS, 0.008), PURPLE)

    play_scene(track or audio.pick("ambience", "rattlesnake"), draw)


def witch_bonfire(track=None):
    """Several bonfires burn around the house, throwing a shower of sparks at every crackle."""
    flame = np.random.random(NUM_PIXELS)
    sparks = []  # [position, velocity, age]

    def draw(playback, t, dt):
        flame[:] += (np.random.random(NUM_PIXELS) - flame) * min(1.0, dt * 9)
        fires = 0.5 + 0.5 * np.sin(x * 2 * math.pi / 80 + 0.3 * np.sin(t * 0.7))
        heat = fires ** 3 * (0.25 + 0.55 * flame) * (0.6 + 0.4 * playback.loudness())
        for strength in playback.new_onsets():
            if strength > 0.2 and len(sparks) < 30:
                sparks.append([random.uniform(0, NUM_PIXELS), random.uniform(-25, 25), 0.0])
        rgb = tint(heat, RED) + tint(heat ** 2, ORANGE)
        for spark in sparks:
            spark[0] = (spark[0] + spark[1] * dt) % NUM_PIXELS
            spark[2] += dt
            rgb[int(spark[0]) % NUM_PIXELS] += GOLD * max(0.0, 1 - spark[2] / 0.7)
        sparks[:] = [s for s in sparks if s[2] < 0.7]
        return rgb

    play_scene(track or audio.pick("ambience", "bonfire"), draw)


def ghost_ship(track=None):
    """A lighthouse beam sweeps through the fog, which glows when the foghorn sounds."""
    def draw(playback, t, dt):
        horn = playback.loudness()
        beam = np.exp(-(distance(x, (t * 45) % NUM_PIXELS) / 16) ** 2)
        fog = 0.5 + 0.5 * np.sin(x * 0.03 - t * 0.2) * np.sin(x * 0.011 + t * 0.13)
        return tint(beam * 0.7, PALE) + tint(fog * (0.02 + 0.25 * horn), PALE * np.array([0.5, 0.7, 0.8]))

    play_scene(track or audio.pick("ambience", "foghorn"), draw)


def dripping_crypt(track=None):
    """Water drips in a black crypt; every drop lands with a pale ring that spreads and fades."""
    rings = []  # [position, start]

    def draw(playback, t, dt):
        now = playback.t
        for strength in playback.new_onsets():
            if strength > 0.2 and len(rings) < 10:
                rings.append([random.uniform(0, NUM_PIXELS), now])
        rgb = tint(np.full(NUM_PIXELS, 0.01), PALE)
        for position, start in rings:
            age = now - start
            rgb += tint(np.exp(-((distance(x, position) - age * 25) / 2.5) ** 2) * 0.6 * math.exp(-age / 0.8), PALE)
        rings[:] = [r for r in rings if now - r[1] < 3]
        return rgb

    play_scene(track or audio.pick("ambience", "cave"), draw)


def cursed_music_box(track=None):
    """A music box winds down, a pink note twinkling for each chime as the ring slowly turns."""
    notes = []  # [position, age]

    def draw(playback, t, dt):
        for strength in playback.new_onsets():
            if strength > 0.1 and len(notes) < 24:
                notes.append([random.uniform(0, NUM_PIXELS), 0.0])
        rgb = tint(0.015 + 0.015 * np.sin(x * 2 * math.pi / 50 + t * 0.4), PURPLE)
        for note in notes:
            note[1] += dt
            rgb += tint(np.exp(-(distance(x, (note[0] + t * 6) % NUM_PIXELS) / 2) ** 2) * math.exp(-note[1] / 1.2), PINK)
        notes[:] = [n for n in notes if n[1] < 3]
        return rgb

    play_scene(track or audio.pick("ambience", "music"), draw)


def zombie_shamble(track=None):
    """Sickly green zombies lurch around the house, a clumsy step forward with every groan."""
    zombies = [[random.uniform(0, NUM_PIXELS), random.choice((-1, 1))] for _ in range(6)]

    def draw(playback, t, dt):
        groan = playback.loudness()
        rgb = tint(np.full(NUM_PIXELS, 0.012), RED)
        for strength in playback.new_onsets():
            if strength > 0.15:
                for zombie in zombies:
                    zombie[0] = (zombie[0] + zombie[1] * random.uniform(1, 6)) % NUM_PIXELS
        for position, _ in zombies:
            rgb += tint(np.exp(-(distance(x, position) / 5) ** 2) * (0.2 + 0.6 * groan), SICKLY)
        return rgb

    play_scene(track or audio.pick("ambience", "zombie"), draw)


def stalker(track=None):
    """Red footprints creep closer around the house with each step, until the scream floods it red."""
    step = [random.randrange(NUM_PIXELS)]
    prints = np.zeros(NUM_PIXELS)
    scream = [0.0]

    def draw(playback, t, dt):
        for strength in playback.new_onsets(low=True):
            if strength > 0.2:
                step[0] = (step[0] + 9) % NUM_PIXELS
                prints[(step[0] + np.arange(3)) % NUM_PIXELS] = 1.0
        prints[:] *= 0.5 ** (dt / 3)
        high = playback.level("high")
        scream[0] = max(high if high > 0.75 else 0.0, scream[0] * 0.5 ** (dt / 0.2))
        return tint(prints * 0.7 + scream[0] * 0.9, RED)

    play_scene(track or audio.pick("ambience", "footsteps"), draw)


def alien_signal(track=None):
    """Radio from Saturn: each band of the eerie signal scans around the house in cold cyan and green."""
    def draw(playback, t, dt):
        bands = playback.bands()
        rgb = np.zeros((NUM_PIXELS, 3))
        for b, level in enumerate(bands):
            wave = 0.5 + 0.5 * np.sin(x * (0.02 + 0.012 * b) - t * (0.5 + 0.25 * b) + b)
            rgb += tint(wave ** 4 * float(level) * 0.28, GREEN * 0.4 + PALE * 0.6 if b % 2 else PALE * np.array([0.2, 1.0, 0.9]))
        return rgb

    play_scene(track or audio.pick("ambience", "saturn"), draw)


def ghost_voices(track=None):
    """Pale figures drift along the house, brightening as the voices rise around them."""
    ghosts = [[random.uniform(0, NUM_PIXELS), random.uniform(-7, 7), random.uniform(0, 6)] for _ in range(5)]

    def draw(playback, t, dt):
        voices = playback.loudness()
        rgb = tint(np.full(NUM_PIXELS, 0.008), PURPLE)
        for ghost in ghosts:
            ghost[0] = (ghost[0] + ghost[1] * dt) % NUM_PIXELS
            level = (0.08 + 0.55 * voices) * (0.65 + 0.35 * math.sin(t * 0.8 + ghost[2]))
            rgb += tint(np.exp(-(distance(x, ghost[0]) / 9) ** 2) * level, PALE)
        return rgb

    play_scene(track or audio.pick("ambience", "ghostly"), draw)


def banshee(track=None):
    """A banshee screeches past in a white and violet streak; the louder the wail, the faster she flies."""
    at = [random.uniform(0, NUM_PIXELS)]

    def draw(playback, t, dt):
        wail = playback.loudness()
        at[0] = (at[0] + (10 + 220 * wail) * dt) % NUM_PIXELS
        behind = (at[0] - x) % NUM_PIXELS
        streak = np.exp(-behind / (4 + 30 * wail)) * (0.15 + 0.85 * wail)
        return tint(streak, PURPLE) + tint(streak ** 3, PALE)

    play_scene(track or audio.pick("ambience", "banshee"), draw)


def locust_plague(track=None):
    """A humming plague boils across the house: a dark swarm that thickens with the drone."""
    def draw(playback, t, dt):
        drone = playback.loudness()
        cloud = 0.5 + 0.5 * np.sin(x * 0.035 - t * 0.9) * np.sin(x * 0.013 + t * 0.4)
        specks = np.random.random(NUM_PIXELS) < cloud * (0.1 + 0.5 * drone)
        return tint(specks * (0.15 + 0.5 * drone), ORANGE) + tint(cloud * 0.03, RED)

    play_scene(track or audio.pick("ambience", "beehive"), draw)


SOUNDSCAPES = [owl_watch, thunderstorm, wolf_moon, ravens, creaking_door, will_o_wisps, midnight_bell,
               witch_cackle, beast_in_the_dark, telltale_heart, something_breathing, witching_hour, clock_tower,
               bat_swarm, graveyard_crickets, swamp_chorus, serpent, witch_bonfire, ghost_ship, dripping_crypt,
               cursed_music_box, zombie_shamble, stalker, alien_signal, ghost_voices, banshee, locust_plague]
KEYWORDS = [
    (("owl",), owl_watch),
    (("thunder", "storm", "lightning"), thunderstorm),
    (("wolf", "wolves"), wolf_moon),
    (("crow", "raven"), ravens),
    (("door", "creak"), creaking_door),
    (("wind",), will_o_wisps),
    (("bell", "toll", "chime"), midnight_bell),
    (("witch",), witch_cackle),
    (("monster",), beast_in_the_dark),
    (("heartbeat",), telltale_heart),
    (("heavy", "breathing"), something_breathing),
    (("ticking",), witching_hour),
    (("strikes",), clock_tower),
    (("bats",), bat_swarm),
    (("crickets",), graveyard_crickets),
    (("frogs",), swamp_chorus),
    (("rattlesnake",), serpent),
    (("bonfire",), witch_bonfire),
    (("foghorn",), ghost_ship),
    (("cave",), dripping_crypt),
    (("music",), cursed_music_box),
    (("zombie",), zombie_shamble),
    (("footsteps",), stalker),
    (("saturn",), alien_signal),
    (("ghostly",), ghost_voices),
    (("banshee",), banshee),
    (("beehive",), locust_plague),
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

FAVORITE_SONGS = ("thriller", "monster")  # file names starting with these come up more often
FAVORITE_ODDS = 1 / 3

recent = []  # names of recently played soundscapes, to avoid repeats
recent_songs = []


def fits(seconds):
    """Whether something this long can finish before the scheduled off time."""
    return not lights.schedule_on or lights.is_show_time(seconds)


def announce(scene):
    print(time.strftime("%H:%M:%S"), scene.__name__, flush=True)
    if on_scene:
        on_scene(scene.__name__)


def play_soundscape():
    global scene_seconds
    track = audio.pick("ambience", avoid=recent[-16:])
    if track is None or not fits(min(track.duration, SCENE_SECONDS)):
        return quiet_glow()
    recent.append(track.name)
    scene = scene_for(track)
    announce(scene)
    scene_seconds = SCENE_SECONDS
    try:
        scene(track)
    finally:
        scene_seconds = None


def play_reds():
    if not fits(SCENE_SECONDS):
        return quiet_glow()
    pattern = random.choice(PATTERNS)
    announce(pattern)
    pattern()


def play_song():
    favorites = [t.name for t in audio.library("music") if t.has_word(*FAVORITE_SONGS)]
    song = None
    if [name for name in favorites if name not in recent_songs[-2:]] and random.random() < FAVORITE_ODDS:
        song = audio.pick("music", *FAVORITE_SONGS, avoid=recent_songs[-2:])
    song = song or audio.pick("music", avoid=recent_songs[-6:])
    if song is not None and fits(song.duration):
        recent_songs.append(song.name)
        visual = random.choice(VISUALIZERS)
        announce(visual)
        visual(song)


def halloween_night():
    """The full show: a new soundscape about every minute, now and then Halloween reds, and every so often a song."""
    for _ in range(REDS_BEFORE_SONG):
        for _ in range(SCENES_BEFORE_REDS):
            play_soundscape()
        play_reds()
    play_song()


if __name__ == "__main__":
    rotate([halloween_night], seconds=1, shuffle=False, scheduled=True)
