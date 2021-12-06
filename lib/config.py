import board
import neopixel

PIXEL_PIN = board.D18
NUM_PIXELS = 50
ORDER = neopixel.GRB

# Visualizations
FPS = 60
MIC_RATE = 44100
MIN_FREQUENCY = 200
MAX_FREQUENCY = 12000
N_ROLLING_HISTORY = 2
N_FFT_BINS = 24