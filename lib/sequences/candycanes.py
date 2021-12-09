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

RED = [0, 255, 0]
WHITE = [255, 255, 255]

def write(data):
    global last_data
    for i in range(0, len(data)):
        pixels[i] = data[i]
    pixels.show()

CANDYCANE_SIZE = 10
NUM_CANES = int(NUM_PIXELS / CANDYCANE_SIZE)

data = np.empty([NUM_PIXELS, 3], dtype=int)
for i in range(0, NUM_CANES):
    for j in range(i * CANDYCANE_SIZE, i * CANDYCANE_SIZE + CANDYCANE_SIZE):
        if i % 2 == 0:
            data[j] = RED
        else:
            data[j] = WHITE
write(data)
time.sleep(2)

cane_position = 0
counter = 0
current_fade_percent = 0
crossfade_steps = 5
rotated = False
while True:
    for i in range(0, NUM_CANES):
        light = i * CANDYCANE_SIZE + cane_position
        val = int(current_fade_percent / crossfade_steps * 255)
        if i % 2 == 0:
            data[light] = [val, 255, val] if not rotated else [255 - val, 255, 255 - val]
        else:
            data[light] = [255 - val, 255, 255 - val] if not rotated else [val, 255, val]

    if (counter + 1) % crossfade_steps == 0:
        if i % 2 == 0:
            data[light] = [255, 255, 255] if not rotated else [0, 255, 0]
        else:
            data[light] = [0, 255, 0] if not rotated else [255, 255, 255]
        cane_position = (cane_position + 1) % CANDYCANE_SIZE
        if cane_position % CANDYCANE_SIZE == 0:
            rotated = not rotated

    current_fade_percent = (current_fade_percent + 1) % crossfade_steps
    counter = counter + 1
    write(data)
    time.sleep(.01)