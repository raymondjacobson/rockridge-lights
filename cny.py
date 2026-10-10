import board
import neopixel
from time import sleep

pixels = neopixel.NeoPixel(
    board.D18,
    500,
    pixel_order=neopixel.RGB,
    auto_write=False,
    brightness=0.3
)

red = (255,0,0)
gold = (245, 182, 30)
silver = (100, 100, 100)

def main():
    for i in range(len(pixels)):
        if i % 10 == 1:
            pixels[i] = silver
        elif i % 10 == 2:
            pixels[i] = gold
        else:
            pixels[i] = red
    pixels.show()


if __name__ == "__main__":
    while True:
        main()
        sleep(1)