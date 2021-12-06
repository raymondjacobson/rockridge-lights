import time
import board
import neopixel
from lib.config import NUM_PIXELS, PIXEL_PIN, ORDER

pixels = neopixel.NeoPixel(
    PIXEL_PIN,
    NUM_PIXELS,
    pixel_order=ORDER
)

last_data = np.empty([NUM_PIXELS, 3], dtype=int)
def write(data):
    global last_data
    for i in range(0, len(data)):
        # if not np.array_equal(last_data[i], data[i]):
        pixels[i] = data[i]
    last_data = data

while True:
    pixels.fill((255, 0, 0))
    time.sleep(60)
    pixels.fill((0, 255, 0))
    time.sleep(60)
