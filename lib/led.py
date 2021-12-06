import numpy as np
import board
import neopixel
from lib.config import NUM_PIXELS, PIXEL_PIN, ORDER
from lib.visualizers import scroll
from lib import config

pixels = neopixel.NeoPixel(
    board.D18,
    NUM_PIXELS,
    pixel_order=neopixel.GRB,
    auto_write=False
)

CHUNK = 1024

_prev_pixels = np.empty(NUM_PIXELS)
def write(data):
    global _prev_pixels
    for i in range(len(data)):
        if np.array_equal(data[i], _prev_pixels[i]):
            continue
        pixels[i] = int(data[i])

    _prev_pixels = np.copy(data)
    pixels.show()

def update(stream_data):
    y = np.frombuffer(stream_data, dtype=np.int16)
    y = y.astype(np.float32)[:int(len(y) / 2)]
    rgb = scroll.update(y)
    # import sys
    # sys.exit(1)
    write(rgb)
    # peak = np.average(np.abs(human_data)) * 2
    # power = peak / 40000.
    # r = min(power * 255, 255)
    # g = 0
    # b = 0
    # pixels.fill((g, r, b))

def loading(percent):
    num_lights = int(percent * NUM_PIXELS)
    for i in range(num_lights):
        pixels[i] = (255, 255, 255)
    for i in range(num_lights, NUM_PIXELS):
        pixels[i] = (0, 0, 0)
