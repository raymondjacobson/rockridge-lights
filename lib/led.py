import numpy as np
import board
import neopixel

NUM_PIXELS = 50

pixels = neopixel.NeoPixel(board.D18, NUM_PIXELS, pixel_order=neopixel.GRB)

CHUNK = 1024

def update(data):
	human_data = np.frombuffer(data, dtype=np.int16)
	peak = np.average(np.abs(human_data)) * 2
	power = peak / 40000.
	r = min(power * 255, 255)
	g = 0
	b = 0
	pixels.fill((g, r, b))

def loading(percent):
	num_lights = int(percent * NUM_PIXELS)
	for i in range(num_lights):
		pixels[i] = (255, 255, 255)
	for i in range(num_lights, NUM_PIXELS):
		pixels[i] = (0, 0, 0)
