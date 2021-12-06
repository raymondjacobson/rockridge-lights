import numpy as np
from lib.visualizers import dsp
from lib import config
from scipy.ndimage.filters import gaussian_filter1d

samples_per_frame = int(config.MIC_RATE / config.FPS)
y_roll = np.random.rand(config.N_ROLLING_HISTORY, samples_per_frame) / 1e16

fft_plot_filter = dsp.ExpFilter(
    np.tile(1e-1, config.N_FFT_BINS),
    alpha_decay=0.5, alpha_rise=0.99
)
mel_gain = dsp.ExpFilter(
    np.tile(1e-1, config.N_FFT_BINS),
    alpha_decay=0.01, alpha_rise=0.99
)
mel_smoothing = dsp.ExpFilter(
    np.tile(1e-1, config.N_FFT_BINS),
    alpha_decay=0.5, alpha_rise=0.99
)
fft_window = np.hamming(
    int(config.MIC_RATE / config.FPS) * config.N_ROLLING_HISTORY
)
gain = dsp.ExpFilter(
    np.tile(0.01, config.N_FFT_BINS),
    alpha_decay=0.001, alpha_rise=0.99
)
p = np.tile(1.0, (3, config.NUM_PIXELS // 2))

def update(samples):
    """Effect that originates in the center and scrolls outwards"""
    global y_roll, p

    y = samples / 2.0**15
    # Construct a rolling window of audio samples
    y_roll[:-1] = y_roll[1:]
    y_roll[-1, :] = np.copy(y)
    y_data = np.concatenate(y_roll, axis=0).astype(np.float32)
    
    # Transform audio input into the frequency domain
    N = len(y_data)
    N_zeros = 2**int(np.ceil(np.log2(N))) - N
    # Pad with zeros until the next power of two
    y_data *= fft_window
    y_padded = np.pad(y_data, (0, N_zeros), mode='constant')
    YS = np.abs(np.fft.rfft(y_padded)[:N // 2])
    # Construct a Mel filterbank from the FFT data
    mel = np.atleast_2d(YS).T * dsp.mel_y.T
    # Scale data to values more suitable for visualization
    # mel = np.sum(mel, axis=0)
    mel = np.sum(mel, axis=0)
    mel = mel**2.0
    # Gain normalization
    mel_gain.update(np.max(gaussian_filter1d(mel, sigma=1.0)))
    mel /= mel_gain.value
    mel = mel_smoothing.update(mel)
    # Map filterbank output onto LED strip

    y = mel**2.0
    gain.update(y)
    y /= gain.value
    y *= 255.0
    r = int(np.max(y[:len(y) // 3]))
    g = int(np.max(y[len(y) // 3: 2 * len(y) // 3]))
    b = int(np.max(y[2 * len(y) // 3:]))
    # Scrolling effect window
    p[:, 1:] = p[:, :-1]
    p *= 0.98
    p = gaussian_filter1d(p, sigma=0.2)
    # Create new color originating at the center
    p[0, 0] = r
    p[1, 0] = g
    p[2, 0] = b
    # Update the LED strip
    concat_p = np.concatenate((p[:, ::-1], p), axis=1)
    clip_p = np.clip(concat_p, 0, 255).astype(int)
    copy_p = np.copy(clip_p)

    # r = np.left_shift(copy_p[0][:].astype(int), 8)
    # print(r)
    # g = np.left_shift(copy_p[1][:].astype(int), 16)
    r = copy_p[0][:].astype(int)
    g = copy_p[1][:].astype(int)
    b = copy_p[2][:].astype(int)

    # print('\n\n\n')
    # print(r)
    # print(g)
    # print(b)
    rgb = np.bitwise_or(np.bitwise_or(r, g), b)

    return rgb
