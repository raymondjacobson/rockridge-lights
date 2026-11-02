"""The shows the control panel can play, and how to play a pick from one.

A pick is a program id, optionally one animation in it, and for the sound
show optionally one track.
For "effects", a pick can instead carry an `effect` made to order (effects.py).
"""
import audio
import effects
import evening
import halloween26
import halloween_audio
import test_white
import xmas25

PROGRAMS = [
    {"id": "evening", "name": "Evening", "seconds": evening.SECONDS, "shuffle": False, "animations": evening.ANIMATIONS},
    {"id": "halloween_audio", "name": "Halloween with sound", "seconds": 1, "shuffle": False,
     "play_all": [halloween_audio.halloween_night],
     "animations": halloween_audio.SOUNDSCAPES + halloween_audio.VISUALIZERS},
    {"id": "halloween26", "name": "Halloween reds", "seconds": halloween26.PATTERN_SECONDS,
     "play_all": halloween26.PATTERNS, "animations": halloween26.PATTERNS + [halloween26.red_sweep]},
    {"id": "xmas25", "name": "Christmas 2025", "seconds": 30, "animations": xmas25.ANIMATIONS},
    {"id": "effects", "name": "Effects", "seconds": effects.SECONDS, "animations": effects.PRESETS},
    {"id": "tests", "name": "Tests", "seconds": 30, "animations": [test_white.white_circle]},
]
PROGRAM = {p["id"]: p for p in PROGRAMS}


def build(program, animation=None, track=None, effect=None):
    """(animations, seconds, shuffle) to hand to lights.rotate() for a pick."""
    p = PROGRAM[program]
    if effect:
        return [effects.animation(effect)], effects.SECONDS, False
    if track and audio.find(track).kind == "music":  # songs always get the full light show
        return [play_track(audio.find(track))], p["seconds"], p.get("shuffle", True)
    animations = p.get("play_all", p["animations"])
    if animation:
        animations = [a for a in p["animations"] if a.__name__ == animation][:1]
        if not animations:
            raise ValueError("{} has no animation {}".format(p["name"], animation))
    if track:
        animations = [play_track(audio.find(track), animations[0] if animation else None)]
    return animations, p["seconds"], p.get("shuffle", True)


def play_track(track, visual=None):
    """An animation that plays `track` once, with its soundscape or a song visualizer."""
    if visual is None:
        visual = halloween_audio.scene_for(track) if track.kind == "ambience" else halloween_audio.graveyard_concert

    def animation():
        visual(track)
    animation.__name__ = visual.__name__
    return animation
