import numpy as np
from lib.config import NUM_PIXELS, PIXEL_PIN, ORDER

lookback_size = 0
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
    r = min(power * 255, 255)
    g = 0
    b = 0
    return (
        np.full(NUM_PIXELS, g),
        np.full(NUM_PIXELS, r),
        np.full(NUM_PIXELS, b)
    )
