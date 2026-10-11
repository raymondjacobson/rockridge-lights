"""Shared setup for the standalone light shows.

A show script imports the strip from here, defines its animations, and
hands them to rotate():

    from lights import pixels, NUM_PIXELS, rotate

    def my_animation():
        ...
        pixels.show()

    if __name__ == "__main__":
        rotate([my_animation])

Pass `scheduled=True` to rotate() to run only from 30 minutes before sunset
until midnight, staying dark (but running) the rest of the day.

Run it with `nohup python <show>.py &`. Killing the process (Ctrl-C or
`kill <pid>`) turns the lights off instead of freezing the last frame.
"""
from datetime import datetime, timedelta, timezone
import math
import random
import signal
import sys
import time

import board
import neopixel

NUM_PIXELS = 400
BRIGHTNESS = 0.4

# Scheduled shows come on this long before sunset and go off at midnight.
LATITUDE = 37.844  # Rockridge, Oakland
LONGITUDE = -122.251
MINUTES_BEFORE_SUNSET = 30

pixels = neopixel.NeoPixel(
    board.D18,
    NUM_PIXELS,
    pixel_order=neopixel.RGB,
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


def sunset(day):
    """Local sunset time on `day` (NOAA approximation, good to a minute or two)."""
    g = 2 * math.pi / 365 * (day.timetuple().tm_yday - 0.5)
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                       - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g)
            - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g)
            - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    lat = math.radians(LATITUDE)
    hour_angle = math.degrees(math.acos(
        math.cos(math.radians(90.833)) / (math.cos(lat) * math.cos(decl))
        - math.tan(lat) * math.tan(decl)))
    minutes_utc = 720 - 4 * (LONGITUDE - hour_angle) - eqtime
    midnight_utc = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    return (midnight_utc + timedelta(minutes=minutes_utc)).astimezone()


def show_start(day):
    return sunset(day) - timedelta(minutes=MINUTES_BEFORE_SUNSET)


def wait_for_show_time():
    """If it's between midnight and the evening's start time, go dark and wait."""
    now = datetime.now().astimezone()
    start = show_start(now.date())
    if now >= start:
        return
    clear()
    print(time.strftime("%H:%M:%S"), "lights off until", start.strftime("%H:%M"), flush=True)
    while datetime.now().astimezone() < start:
        time.sleep(30)


def rotate(animations, seconds=30, shuffle=True, scheduled=False):
    """Play each animation for about `seconds`, forever.

    Each animation is called repeatedly until its time is up, so it can be
    a single pass or a longer self-contained loop. With `scheduled`, the
    lights only run from MINUTES_BEFORE_SUNSET before sunset until midnight.
    """
    animations = list(animations)
    try:
        while True:
            if shuffle:
                random.shuffle(animations)
            for animation in animations:
                if scheduled:
                    wait_for_show_time()
                print(time.strftime("%H:%M:%S"), animation.__name__, flush=True)
                start_time = time.time()
                while time.time() - start_time < seconds:
                    animation()
    finally:
        clear()
