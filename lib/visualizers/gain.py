import numpy as np
from lib.config import NUM_PIXELS, PIXEL_PIN, ORDER

lookback_size = 1
lookback = []
def update(samples):
    avg = np.average(np.abs(samples))
    max_amp = np.max(np.abs(samples))
    power = avg / max_amp

    if len(lookback) < lookback_size:
        lookback.append(power)
    else:
        lookback.pop(0)
        lookback.append(power)

    power = np.mean(lookback, axis=0)

    g = np.empty(NUM_PIXELS)
    r = np.empty(NUM_PIXELS)
    b = np.empty(NUM_PIXELS)
    for i in range(len(g)):
        if i % 5 == 0:
            # red
            r[i] = power * 255
            g[i] = 0
            b[i] = 0
        elif i % 5 == 1:
            # green
            r[i] = 0
            g[i] = power * 255
            b[i] = 0
        elif i % 5 == 2:
            # blue
            r[i] = 0
            g[i] = 0
            b[i] = power * 255
        elif i % 5 == 3:
            # yellow
            r[i] = power * 255
            g[i] = power * 255
            b[i] = 0
        elif i % 5 == 4:
            # pink
            r[i] = power * 255
            g[i] = int(68 / 255 * power * 255)
            b[i] = int(204 / 255 * power * 255)
            
    return (
        np.full(NUM_PIXELS, g),
        np.full(NUM_PIXELS, r),
        np.full(NUM_PIXELS, b)
    )
