import numpy as np
from lib.config import NUM_PIXELS, PIXEL_PIN, ORDER

MIN_VAL = 10
PREV_VAL = None

lookback_size = 8
lookback = []
def update(samples):
    fft = np.abs(np.fft.fft(samples))
    fft = np.clip((fft / np.amax(fft)) * 255, MIN_VAL, 255)
    if len(lookback) < lookback_size:
        lookback.append(fft)
    else:
        lookback.pop(0)
        lookback.pop(0)
        lookback.pop(0)
        lookback.append(fft)
        lookback.append(fft)
        lookback.append(fft)
    fft = np.mean(lookback, axis=0).astype(int)
    val = np.mean(fft[10])
    g = np.empty(len(fft))
    r = np.empty(len(fft))
    b = np.empty(len(fft))
    for i in range(len(g)):
        if i % 5 == 0:
            # red
            r[i] = val
            g[i] = 0
            b[i] = 0
        elif i % 5 == 1:
            # green
            r[i] = 0
            g[i] = val
            b[i] = 0
        elif i % 5 == 2:
            # blue
            r[i] = 0
            g[i] = 0
            b[i] = val
        elif i % 5 == 3:
            # yellow
            r[i] = val
            g[i] = val
            b[i] = 0
        elif i % 5 == 4:
            # pink
            r[i] = val
            g[i] = int(68 / 255 * val)
            b[i] = int(204 / 255 * val)
    return (g, r, b)