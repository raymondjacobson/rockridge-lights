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
volume = dsp.ExpFilter(
    config.MIN_VOLUME_THRESHOLD,
    alpha_decay=0.02, alpha_rise=0.02
)

CHUNK = 1024

def write(g, r, b):
    for i in range(NUM_PIXELS):
        pixels[i] = (int(g[i]), int(r[i]), int(b[i]))
    pixels.show()

def update(stream_data):
    y = np.frombuffer(stream_data, dtype=np.int16)
    y = y.astype(np.float32)[:int(len(y) / 2)]
    vol = np.max(np.abs(y))
    if vol < config.MIN_VOLUME_THRESHOLD:
        print('No audio input. Volume below threshold. Volume:', vol)
        return
    # (g, r, b) = scroll.update(y)
    # (g, r, b) = gain.update(y)
    # (g, r, b) = fft.update(y)
    (g, r, b) = topfft.update(y)
    write(g, r, b)

def loading(percent):
    num_lights = int(percent * NUM_PIXELS)
    for i in range(num_lights):
        pixels[i] = (255, 255, 255)
    for i in range(num_lights, NUM_PIXELS):
        pixels[i] = (0, 0, 0)
