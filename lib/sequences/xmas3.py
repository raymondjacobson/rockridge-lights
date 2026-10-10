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

from rpi_ws281x import *
strip = Adafruit_NeoPixel(
    NUM_PIXELS,
    18,
    800000,
    5,
    False,
    100 
)
strip.begin()

def write(data):
    # global last_data
    r = np.array([])
    g = np.array([])
    b = np.array([])
    for i in range(0, len(data)):
        r = np.append(r, data[i][0])
        g = np.append(g, data[i][1])
        b = np.append(b, data[i][2])
        # pixels[i] = data[i]
        # print(data[i])
    r = np.left_shift(r.astype(int), 8)
    g = np.left_shift(g.astype(int), 16)
    b = b.astype(int)
    rgb = np.bitwise_or(np.bitwise_or(r, g), b)
    for i in range(len(data)):
        strip._led_data[i] = int(rgb[i])
    # pixels.show()
    strip.show()
    # last_data = data

data = np.empty([NUM_PIXELS, 3], dtype=int)
for i in range(NUM_PIXELS):
    if i % 3 == 0:
        data[i] = [255, 0, 0]
    else:
        data[i] = [0, 255, 0]
    g = np.empty(NUM_PIXELS)
    r = np.empty(NUM_PIXELS)
    b = np.empty(NUM_PIXELS)
    for i in range(len(g)):
        if i % 5 == 0:
            # red
            data[i][1] = 100
            data[i][0] = 0
            data[i][2] = 0
        elif i % 5 == 1:
            # green
            data[i][1] = 0
            data[i][0] = 100
            b[i] = 0
        elif i % 5 == 2:
            # blue
            data[i][1] = 0
            data[i][0] = 0
            data[i][2] = 100
        elif i % 5 == 3:
            # yellow
            data[i][1] = 100
            data[i][0] = 100
            data[i][2] = 0
        elif i % 5 == 4:
            # pink
            data[i][1] = 100
            data[i][0] = int(68 / 255 * 100)
            data[i][2] = int(204 / 255 * 100)

while True:
    data = np.roll(data, 1, axis=0)
    write(data)
    time.sleep(1)