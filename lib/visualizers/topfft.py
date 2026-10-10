import numpy as np
from lib.config import NUM_PIXELS, PIXEL_PIN, ORDER

MIN_VAL = 100
PREV_VAL = None

lookback_size = 1
lookback = []
g = np.zeros(NUM_PIXELS)
r = np.zeros(NUM_PIXELS)
b = np.zeros(NUM_PIXELS)
def update(samples):
    fft = np.abs(np.fft.fft(samples))
    fft = np.clip((fft / np.amax(fft)) * 255, MIN_VAL, 255)
    fft = fft[:NUM_PIXELS]
    if len(lookback) < lookback_size:
        lookback.append(fft)
    else:
        lookback.pop(0)
        lookback.append(fft)
    fft = np.mean(lookback, axis=0).astype(int)
    val = np.mean(fft[5:20])

    low = np.mean(fft[0:2])
    mid = np.mean(fft[5])
    high = np.mean(fft[4:100])
    # print(fft[0:20])
    # str = '•' * int(mid / 10)
    # print(str)
    perc = mid / 255
    pos = int(perc * 20)

    for i in range(len(g)):
        if i % pos == 0:
            b[i] = int(mid / 2)
            r[i] = mid
            g[i] = int(mid / 2)
        elif i % pos == 1 or i % pos == pos - 1:
            b[i] = int(mid / 4)
            r[i] = int(mid / 2)
            g[i] = int(mid / 4)
        else:
            b[i] = int(low / 4)
            r[i] = int(low / 4)
            g[i] = int(low / 4)


    # for i in range(len(g)):
    #     if i < 130:
    #         b[i] = int(low / 2)
    #         r[i] = low
    #         g[i] = int(low / 2)
    #     elif i < 260:
    #         b[i] = int(mid / 2)
    #         r[i] = mid
    #         g[i] = mid
    #     else:
    #         b[i] = int(high / 4)
    #         r[i] = int(mid / 4)
    #         g[i] = high
            
        # if high > MIN_VAL:
        #     b[i] = high
        #     r[i] = int(high / 2)
        #     g[i] = int(high / 2)
        # else:
        #     r[i] = mid
        #     g[i] = mid
        #     b[i] = int(mid / 2)
    # for i in range(len(g)):
    #     if i % 5 == 0:
    #         # red
    #         r[i] = val
    #         g[i] = 0
    #         b[i] = 0
    #     elif i % 5 == 1:
    #         # green
    #         r[i] = 0
    #         g[i] = val
    #         b[i] = 0
    #     elif i % 5 == 2:
    #         # blue
    #         r[i] = 0
    #         g[i] = 0
    #         b[i] = val
    #     elif i % 5 == 3:
    #         # yellow
    #         r[i] = val
    #         g[i] = val
    #         b[i] = 0
    #     elif i % 5 == 4:
    #         # pink
    #         r[i] = val
    #         g[i] = int(68 / 255 * val)
    #         b[i] = int(204 / 255 * val)
    return (g, r, b)