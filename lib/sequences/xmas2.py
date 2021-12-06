import time
import board
import neopixel
import numpy as np
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

data = np.empty([NUM_PIXELS, 3], dtype=int)
for i in range(NUM_PIXELS):
    if i % 3 == 0:
        data[i] = [255, 0, 0]
    else:
        data[i] = [0, 255, 0]

while True:
    data = np.roll(data, 1, axis=0)
    write(data)
    time.sleep(1)