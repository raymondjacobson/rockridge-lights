import time
import board
import neopixel
import numpy as np
import random
from lib.config import NUM_PIXELS, PIXEL_PIN, ORDER

import sys
print(sys.path)

pixels = neopixel.NeoPixel(
    PIXEL_PIN,
    NUM_PIXELS,
    pixel_order=ORDER,
    auto_write=False
)

def write(data):
    global last_data
    for i in range(0, len(data)):
        # if not np.array_equal(last_data[i], data[i]):
        pixels[i] = data[i]
    pixels.show()
    last_data = data

data = np.empty([NUM_PIXELS, 3], dtype=int)

for i in range(NUM_PIXELS):
    G = random.randint(0, 255)
    R = random.randint(0, 255)
    B = random.randint(0, 255)
    data[i] = [G, R, B]

while True:
    data = np.roll(data, 1, axis=0)
    write(data)
    time.sleep(.1)