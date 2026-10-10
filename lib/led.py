import numpy as np
import board
import neopixel
import time
from lib.visualizers import dsp
from lib.config import NUM_PIXELS, PIXEL_PIN, ORDER, MIN_VOLUME_THRESHOLD
from lib.visualizers import scroll, gain, fft, topfft
from lib import config


pixels = neopixel.NeoPixel(
    board.D18,
    NUM_PIXELS,
    pixel_order=neopixel.GRB,
    auto_write=False
)
from rpi_ws281x import *
strip = Adafruit_NeoPixel(
    NUM_PIXELS,
    18,
    800000,
    5,
    False,
    10
)
strip.begin()

volume = dsp.ExpFilter(
    config.MIN_VOLUME_THRESHOLD,
    alpha_decay=0.02, alpha_rise=0.02
)

_prev_pixels = np.zeros(NUM_PIXELS, dtype=int)
CHUNK = 1024
def write(g, r, b):
    global _prev_pixels
    r = np.left_shift(r.astype(int), 8)
    g = np.left_shift(g.astype(int), 16)
    b = b.astype(int)
    rgb = np.bitwise_or(np.bitwise_or(r, g), b)
    for i in range(len(rgb)):
         # Ignore pixels if they haven't changed (saves bandwidth)
        # if np.array_equal(p[:, i], _prev_pixels[:, i]):
        #     continue
        # if np.array_equal(_prev_pixels[i], rgb[i]):
        #     continue
        strip._led_data[i] = int(rgb[i])
    # _prev_pixels = np.copy(rgb)
    strip.show()

# def write(g, r, b):
#     for i in range(NUM_PIXELS):
#         pixels[i] = (int(g[i]), int(r[i]), int(b[i]))
#     pixels.show()

def update(stream_data):
    y = np.frombuffer(stream_data, dtype=np.int16)
    y = y.astype(np.float32)[:int(len(y) / 2)]
    vol = np.max(np.abs(y))
    if vol < config.MIN_VOLUME_THRESHOLD:
        print('No audio input. Volume below threshold. Volume:', vol)
        return
    # (g, r, b) = scroll.update(y)
    (g, r, b) = gain.update(y)
    # (g, r, b) = fft.update(y)
    # (g, r, b) = topfft.update(y)
    write(g, r, b)

def loading(percent):
    num_lights = int(percent * NUM_PIXELS)
    for i in range(num_lights):
        pixels[i] = (255, 255, 255)
    for i in range(num_lights, NUM_PIXELS):
        pixels[i] = (0, 0, 0)
