"""Shared setup for the light shows.

A show script imports the strip from here, defines its animations, and
hands them to rotate():

    from lights import pixels, NUM_PIXELS, rotate

    def my_animation():
        ...
        pixels.show()

    if __name__ == "__main__":
        rotate([my_animation])

Pass `scheduled=True` to rotate() to run only from 30 minutes before sunset
until 11:59pm, staying dark (but running) the rest of the day.

Run it with `nohup python <show>.py &`. Killing the process (Ctrl-C or
`kill <pid>`) turns the lights off instead of freezing the last frame.

The control panel (panel.py) imports the same animations and previews them
in a browser; `pixels` only drives the real LEDs while `pixels.to_leds` is on.
"""
from datetime import datetime, timedelta, timezone
import math
import random
import signal
import sys
import threading
import time
import weakref

try:
    import board
    import neopixel
except (ImportError, NotImplementedError):  # not on the Pi: preview only
    board = neopixel = None

NUM_PIXELS = 400
BRIGHTNESS = 0.4

# Scheduled shows come on this long before sunset and go off at OFF_HOUR:OFF_MINUTE.
LATITUDE = 37.844  # Rockridge, Oakland
LONGITUDE = -122.251
MINUTES_BEFORE_SUNSET = 30
OFF_HOUR = 23
OFF_MINUTE = 59

OFF = (0, 0, 0)
WHITE = (255, 255, 255)


class Stopped(BaseException):
    """Raised from pixels.show() when the control panel switches to another show."""


class Strip:
    """The frame the shows draw into: set `pixels[i] = (r, g, b)`, then `pixels.show()`.

    show() sends the frame to the LEDs while `to_leds` is on, and to every
    function in `listeners` (the control panel's preview).
    """

    def __init__(self, n):
        self.n = n
        self.buffer = [OFF] * n
        self.brightness = BRIGHTNESS
        self.to_leds = True
        self.listeners = []
        self.interrupt = threading.Event()
        self.retired = weakref.WeakSet()  # stopped show threads, kept off the strip if they linger
        self._leds = None
        self._lock = threading.RLock()

    def __len__(self):
        return self.n

    def __getitem__(self, index):
        return self.buffer[index]

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            self.buffer[index] = [tuple(color) for color in value]
        else:
            self.buffer[index] = tuple(value)

    def fill(self, color):
        self.buffer = [tuple(color)] * self.n

    def stopped(self):
        """Whether the show drawing from this thread has been told to stop."""
        return self.interrupt.is_set() or threading.current_thread() in self.retired

    def show(self):
        if self.stopped():
            raise Stopped
        self.send()

    def send(self):
        """Like show(), but also works while the show is being stopped."""
        if threading.current_thread() in self.retired:
            raise Stopped
        with self._lock:
            if self.to_leds:
                leds = self._open_leds()
                if leds.brightness != self.brightness:
                    leds.brightness = self.brightness
                leds[:] = self.buffer
                leds.show()
        for listener in self.listeners:
            listener(self.buffer)

    def _open_leds(self):
        if self._leds is None:
            if neopixel is None:
                raise RuntimeError("no LED strip on this machine")
            self._leds = neopixel.NeoPixel(board.D18, self.n, pixel_order=neopixel.RGB,
                                           auto_write=False, brightness=self.brightness)
        return self._leds

    def release_leds(self):
        """Turn the LEDs off and let go of them so another process can use them."""
        if not self._lock.acquire(timeout=3):  # a stuck show has them; the panel restarts
            return
        try:
            self._release_leds()
        finally:
            self._lock.release()

    def _release_leds(self):
        if self._leds is not None:
            self._leds.fill(OFF)
            self._leds.show()
            self._leds.deinit()
            self._leds = None


pixels = Strip(NUM_PIXELS)


def clear():
    """Turn every light off."""
    pixels.fill(OFF)
    pixels.send()


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


def show_end(day):
    return show_start(day).replace(hour=OFF_HOUR, minute=OFF_MINUTE, second=0, microsecond=0)


def is_show_time(seconds=0):
    """Whether the next `seconds` fall inside tonight's show window."""
    now = datetime.now().astimezone()
    return show_start(now.date()) <= now and now + timedelta(seconds=seconds) <= show_end(now.date())


def next_show_start():
    now = datetime.now().astimezone()
    start = show_start(now.date())
    return start if now < start else show_start(now.date() + timedelta(days=1))


def wait_for_show_time(seconds):
    """Go dark and wait unless the next `seconds` fit before the off time."""
    if is_show_time(seconds):
        return
    clear()
    start = next_show_start()
    print(time.strftime("%H:%M:%S"), "lights off until", start.strftime("%H:%M"), flush=True)
    while datetime.now().astimezone() < start:
        if pixels.interrupt.wait(30) or pixels.stopped():
            raise Stopped


schedule_on = False  # whether the running rotate() follows the schedule


def rotate(animations, seconds=30, shuffle=True, scheduled=False):
    """Play each animation for about `seconds`, forever.

    Each animation is called repeatedly until its time is up, so it can be
    a single pass or a longer self-contained loop. With `scheduled`, the
    lights only run from MINUTES_BEFORE_SUNSET before sunset until
    OFF_HOUR:OFF_MINUTE (a pattern that would run past it isn't started).
    """
    global schedule_on
    schedule_on = scheduled
    animations = list(animations)
    try:
        while True:
            if shuffle:
                random.shuffle(animations)
            for animation in animations:
                if scheduled:
                    wait_for_show_time(seconds)
                print(time.strftime("%H:%M:%S"), animation.__name__, flush=True)
                start_time = time.time()
                while time.time() - start_time < seconds:
                    animation()
    finally:
        clear()
