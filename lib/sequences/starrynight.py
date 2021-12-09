import time
import board
import neopixel
import numpy as np
import random
from lib.config import NUM_PIXELS, PIXEL_PIN, ORDER

pixels = neopixel.NeoPixel(
    PIXEL_PIN,
    NUM_PIXELS,
    pixel_order=ORDER,
    auto_write=False
)

def write(data):
    global last_data
    for i in range(0, len(data)):
        pixels[i] = data[i]
    pixels.show()
    last_data = data

data = np.tile(np.array([150, 150, 150]), (NUM_PIXELS, 1))

lookback_size = 2
lookback = []
while True:
    for i in range(len(data)):
        if random.randint(0, 1) == 1:
            data[i] = data[i] - np.random.normal(0, 10)
        else:
            data[i] = data[i] + np.random.normal(0, 10)
    data = np.clip(data, 0, 255).astype(int)
    if len(lookback) < lookback_size:
        lookback.append(data)
    else:
        lookback.pop(0)
        lookback.append(data)
    data = np.mean(lookback, axis=0).astype(int)
    write(data)
    time.sleep(.1)
