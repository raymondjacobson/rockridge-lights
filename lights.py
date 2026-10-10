"""Shared setup for the standalone light shows.

A show script imports the strip from here, defines its animations, and
hands them to rotate():

    from lights import pixels, NUM_PIXELS, rotate

    def my_animation():
        ...
        pixels.show()

    if __name__ == "__main__":
        rotate([my_animation])

Run it with `nohup python <show>.py &`. Killing the process (Ctrl-C or
`kill <pid>`) turns the lights off instead of freezing the last frame.
"""
import random
import signal
import sys
import time

import board
import neopixel

NUM_PIXELS = 400
BRIGHTNESS = 0.4

pixels = neopixel.NeoPixel(
    board.D18,
    NUM_PIXELS,
    pixel_order="BRG",  # this strip takes blue, red, green (not the usual RGB)
    auto_write=False,
    brightness=BRIGHTNESS
)

OFF = (0, 0, 0)
WHITE = (255, 255, 255)


def clear():
    """Turn every light off."""
    pixels.fill(OFF)
    pixels.show()


# `kill <pid>` sends SIGTERM; turn it into a normal exit so rotate() can clear.
signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))


def rotate(animations, seconds=30, shuffle=True):
    """Play each animation for about `seconds`, forever.

    Each animation is called repeatedly until its time is up, so it can be
    a single pass or a longer self-contained loop.
    """
    animations = list(animations)
    try:
        while True:
            if shuffle:
                random.shuffle(animations)
            for animation in animations:
                start_time = time.time()
                while time.time() - start_time < seconds:
                    animation()
    finally:
        clear()
