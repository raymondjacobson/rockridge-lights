"""Quiet everyday looks for the evenings, no sound: the house's background between the holidays."""
import numpy as np

from halloween26 import frames, show, x
from lights import NUM_PIXELS

SECONDS = 600  # how long each call runs; rotate() calls it again
FADE_IN = 8

# LEDs at full white look cold, so a warm yellow white is red and green with hardly any blue.
GOLDEN = np.array([1.0, 0.62, 0.08])
SOFT = np.array([1.0, 0.72, 0.15])

GLOW = (0.05, 0.085)  # every light's steady level, a little different per light
PEAK = (0.16, 0.30)  # how high a twinkle swells
RISE = (1.0, 2.2)  # seconds
FALL = (2.0, 4.5)  # seconds
TWINKLES_PER_SECOND = 7  # across all 400 lights


class Twinkles:
    def __init__(self, seed=None):
        self.random = np.random.RandomState(seed)
        r = self.random
        self.t = 0.0
        self.glow = r.uniform(*GLOW, NUM_PIXELS)
        self.color = SOFT + (GOLDEN - SOFT) * r.random_sample(NUM_PIXELS)[:, None]
        self.drift = r.uniform(0, 2 * np.pi, NUM_PIXELS)  # each light's glow wanders a little too
        self.since = np.full(NUM_PIXELS, np.inf)  # seconds since each light's twinkle began
        self.rise = np.ones(NUM_PIXELS)
        self.fall = np.ones(NUM_PIXELS)
        self.peak = np.zeros(NUM_PIXELS)

    def draw(self, dt):
        """This frame's colors, (N, 3), 0..1."""
        r = self.random
        dt = min(dt, 0.25)  # a stall doesn't skip the twinkles ahead
        self.t += dt
        self.since += dt

        resting = np.flatnonzero(self.since >= self.rise + self.fall)
        count = min(len(resting), r.poisson(TWINKLES_PER_SECOND * dt))
        if count:
            new = r.choice(resting, count, replace=False)
            self.since[new] = 0.0
            self.rise[new] = r.uniform(*RISE, count)
            self.fall[new] = r.uniform(*FALL, count)
            self.peak[new] = r.uniform(*PEAK, count)

        # eases up and down, so nothing ever snaps on or off
        up = np.clip(self.since / self.rise, 0, 1)
        down = np.clip((self.since - self.rise) / self.fall, 0, 1)
        swell = (0.5 - 0.5 * np.cos(np.pi * up)) * (0.5 + 0.5 * np.cos(np.pi * down))

        # very slow, faint waves around the house, so it isn't mechanically even
        wave = 1 + 0.12 * np.sin(x / 53 + self.t * 0.07) + 0.08 * np.sin(x / 19 - self.t * 0.04)
        glow = self.glow * wave * (1 + 0.1 * np.sin(self.t * 0.25 + self.drift))
        level = glow + (self.peak - glow).clip(0) * swell
        return level[:, None] * self.color


def warm_twinkle():
    """A low warm white glow, with single lights slowly swelling and fading like distant candles."""
    for t, dt, fade in frames(SECONDS):
        # fade in once at the start, but don't dip when rotate() calls this again
        show(twinkles.draw(dt), min(1.0, twinkles.t / FADE_IN))


twinkles = Twinkles()
ANIMATIONS = [warm_twinkle]
