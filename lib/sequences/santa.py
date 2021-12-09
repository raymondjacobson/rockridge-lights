import time
import board
import neopixel
import numpy as np
from lib.config import NUM_PIXELS, PIXEL_PIN, ORDER

pixels = neopixel.NeoPixel(
    PIXEL_PIN,
    NUM_PIXELS,
    pixel_order=ORDER,
    auto_write=False
)

def write(data):
    global last_data
    for i in range(0, len(data)):
        pixels[i] = data[i]
    pixels.show()
    last_data = data

data = np.tile(np.array([0, 0, 0]), (NUM_PIXELS, 1))
data[0] = [155, 195, 119]
data[1] = [155, 195, 119]
data[2] = [61, 31, 12]
data[3] = [61, 31, 12]
data[4] = [155, 195, 119]
data[5] = [70, 189, 81]
data[6] = [155, 195, 119]
data[7] = [155, 195, 119]

data[10] = [226, 252, 62] 
data[12] = [226, 252, 62]
data[14] = [226, 252, 62]
data[16] = [226, 252, 62]
data[18] = [226, 252, 62]
data[20] = [226, 252, 62]
data[22] = [226, 252, 62]
data[24] = [226, 252, 62]
data[26] = [226, 252, 62]
data[26] = [0, 255, 0]

counter = 1
dim = True
dim_steps = 4.
while True:
    if counter == dim_steps:
        if dim:
            data = np.roll(data, 1, axis=0)
        dim = not dim
        counter = 1
    data_copy = np.copy(data)
    for i in range(len(data)):
        if dim:
            data_copy[i] = ((dim_steps - counter) / (dim_steps) * data_copy[i]).astype(int)
        else:
            data_copy[i] = (counter / (dim_steps) * data_copy[i]).astype(int)
    write(data_copy)
    counter += 1
    time.sleep(.0001)
