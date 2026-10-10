import board
import neopixel
from time import sleep

NUM_PIXELS = 500

pixels = neopixel.NeoPixel(
    board.D18,
    NUM_PIXELS,
    pixel_order=neopixel.RGB,
    auto_write=False,
    brightness=0.3
)

pink = (255,192,203)
maroon = (255,20,147)
num_colors = 2
strands = 5
pixels_in_strand = 100

def set_color_in_strand(i, s, c):
    for j in range(pixels_in_strand):
        p = i+s*pixels_in_strand+j
        if p > NUM_PIXELS - 1:
            p = p - NUM_PIXELS
        pixels[p] = c

def main():
    i = 0
    while True:
        for s in range(strands):
            if s % num_colors == 0:
                set_color_in_strand(i, s, pink)
            elif s % num_colors ==  1:
                set_color_in_strand(i, s, maroon)
        pixels.show()
        sleep(0.25)
        if i == 499:
            i = 0
        else:
            i += 1

if __name__ == "__main__":
    # while True:
    #     main()
    #     sleep(1)
    main()