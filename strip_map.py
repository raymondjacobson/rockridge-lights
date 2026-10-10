"""Diagnostic: color the strip in blocks of 100 to see where it stops."""
from time import sleep

from lights import pixels

BLOCKS = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255), (160, 0, 255)]  # red, green, blue, white, purple

for i in range(len(pixels)):
    pixels[i] = BLOCKS[i // 100]
pixels.show()
while True:
    sleep(60)
