import numpy as np
from lib.config import NUM_PIXELS, PIXEL_PIN, ORDER

lookback_size = 6
lookback = []
def update(samples):
    fft = np.abs(np.fft.fft(samples))
    # pad = NUM_PIXELS - (len(samples) % NUM_PIXELS)
    # fft = np.pad(fft, (0, pad), 'reflect')
    # fft = fft.reshape(-1, NUM_PIXELS)
    # fft = fft.reshape(-1, NUM_PIXELS).mean(axis=0)
    fft = np.clip((fft / np.amax(fft)) * 255, 10, 255)
    if len(lookback) < lookback_size:
        lookback.append(fft)
    else:
        lookback.pop(0)
        lookback.append(fft)
    fft = np.mean(lookback, axis=0).astype(int)
    # fft = np.append(
    #     np.flip(fft[0::2]),
    #     np.flip(fft[0::2]),
    # )
    g = fft
    # r = np.empty(len(fft))
    # r.fill(0)
    r = np.roll(fft, 1, axis=0)
    # b = np.empty(len(fft))
    # b.fill(0)
    b = np.roll(fft, 20, axis=0)
    return (g, r, b)