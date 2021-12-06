import time
import board
import neopixel
from lib.config import NUM_PIXELS, PIXEL_PIN, ORDER

pixels = neopixel.NeoPixel(
    PIXEL_PIN,
    NUM_PIXELS,
    pixel_order=ORDER
)

while True:
    pixels.fill((255, 0, 0))
    for i in range(0, 255):
        time.sleep(.01)
        pixels.fill((255 - i, i, 0))
    time.sleep(30)
    for i in range(0, 255):
        time.sleep(.01)
        pixels.fill((i, 255 - i, 0))
    time.sleep(30)

