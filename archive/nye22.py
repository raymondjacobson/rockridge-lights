import board
import math
import neopixel
import random
from datetime import datetime
from time import sleep

NUM_PIXELS = 500

pixels = neopixel.NeoPixel(
    board.D18,
    NUM_PIXELS,
    pixel_order=neopixel.RGB,
    auto_write=False,
    brightness=1
)

black = (0,0,0)
red = (255,0,0)
green = (0,255,0)
blue = (0,0,100)
orange = (255,165,0)
purple = (128,0,128)

gold = (245, 182, 30)
silver = (100, 100, 100)

batch_length = 10
randomness_rounds = 50
batch_count = math.floor(NUM_PIXELS / batch_length)

def get_random_color():
  G = random.randint(0, 255)
  R = random.randint(0, 255)
  B = random.randint(0, 255)
  return (R, G, B)

def has_passed_midnight():
  return datetime.now() > datetime(2025, 1, 1, 0, 0, 0)

def main():
  # round_no = 0
  # random_batch = random.randint(0, batch_count)
  while True:
    if has_passed_midnight():
      for i in range(NUM_PIXELS):
        pixels[i] = get_random_color()
    else:
      for i in range(batch_count):
        for j in range(batch_length):
          if i % 2 == 0:
            pixels[i * batch_length + j] = gold
          else:
            pixels[i * batch_length + j] = silver

        # if i == random_batch:
        #   for j in range(batch_length):
        #     pixels[i * batch_length + j] = get_random_color()
        #   round_no += 1
        #   if round_no > randomness_rounds:
        #     random_batch = random.randint(0, batch_count)
        #     round_no = 0
    pixels.show()
    sleep(0.025)

if __name__ == "__main__":
    main()
