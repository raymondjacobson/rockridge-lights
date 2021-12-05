import time
import board
import neopixel
import numpy as np

PIXEL_PIN = board.D18
NUM_PIXELS = 50
ORDER = neopixel.GRB

pixels = neopixel.NeoPixel(
    PIXEL_PIN,
    NUM_PIXELS,
    pixel_order=ORDER
)

RED = [0, 255, 0]
WHITE = [255, 255, 255]

last_data = np.empty([NUM_PIXELS, 3], dtype=int)
def write(data):
    global last_data
    for i in range(0, len(pixels)):
        if not np.array_equal(last_data[i], data[i]):
            pixels[i] = data[i]
    last_data = data

CANDYCANE_SIZE = 10
NUM_CANES = int(NUM_PIXELS / CANDYCANE_SIZE)

# cane_position = 0
# while True:
#     data = np.empty([NUM_PIXELS, 3], dtype=int)
#     for i in range(0, NUM_CANES):
#         for j in range(i * CANDYCANE_SIZE, i * CANDYCANE_SIZE + CANDYCANE_SIZE):
#             if i % 2 == 0:
#                 data[j] = RED
#             else:
#                 data[j] = WHITE
#     data = np.roll(data, cane_position, axis=0)
#     write(data)
#     cane_position += 1
#     time.sleep(0.01)

data = np.empty([NUM_PIXELS, 3], dtype=int)
for i in range(0, NUM_CANES):
    for j in range(i * CANDYCANE_SIZE, i * CANDYCANE_SIZE + CANDYCANE_SIZE):
        if i % 2 == 0:
            data[j] = RED
        else:
            data[j] = WHITE
write(data)

def flip(current, percent):
    val = int(percent * 255)
    return [val, 255, val]
    

cane_position = 0
counter = 0
current_fade_percent = 0
while True:
    if counter % 100 == 0:
        cane_position += 1
    for i in range(0, NUM_CANES):
        light = (i * CANDYCANE_SIZE + cane_position) % NUM_PIXELS
        data[light] = flip(last_data, current_fade_percent)
    current_fade_percent = (current_fade_percent + 1) % 100
    print(current_fade_percent)
    write(data)
    time.sleep(0.1)