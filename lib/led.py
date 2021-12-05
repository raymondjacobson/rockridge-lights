import numpy as np
import board
import neopixel

PIXELS = neopixel.NeoPixel(board.D18, 50, pixel_order=neopixel.GRB)

CHUNK = 1024

def update(data):
	human_data = np.frombuffer(data, dtype=np.int16)
	peak = np.average(np.abs(human_data)) * 2
	power = peak / 40000.
	r = min(power * 255, 255)
	g = 0
	b = 0
	PIXELS.fill((g, r, b))