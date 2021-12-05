import time
import board
import neopixel

PIXEL_PIN = board.D18
NUM_PIXELS = 50
ORDER = neopixel.GRB

pixels = neopixel.NeoPixel(
    PIXEL_PIN,
    NUM_PIXELS,
    pixel_order=ORDER
)

CANDYCANE_SIZE = 10

counter = 0
while True:
    for i in range(0, len(pixels)):
        pixels[i] = (255, 0, 0)
    time.sleep(1)