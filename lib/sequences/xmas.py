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

while True:
    pixels.fill((255, 0, 0))
    time.sleep(1)
    pixels.fill((0, 255, 0))
    time.sleep(1)
