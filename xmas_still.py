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
green = (0,255,0)
blue = (0,0,255)
orange = (255,165,0)
yellow = (255,255,0)
purple = (128,0,128)

def main():
    for i in range(len(pixels)):
        if i % num_colors == 0:
            pixels[i] = red
        elif i % num_colors == 1:
            pixels[i] = green
        elif i % num_colors == 2:
            pixels[i] = yellow
        elif i % num_colors == 3:
            pixels[i] = purple
        elif i % num_colors == 4:
            pixels[i] = orange
        elif i % num_colors == 5:
            pixels[i] = blue
        else:
            pixels[i] = red
    pixels.show()

if __name__ == "__main__":
    while True:
        main()
        sleep(1)