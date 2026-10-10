"""Test: a short white segment chasing around the whole strip."""
from time import sleep

from lights import pixels, NUM_PIXELS, OFF, WHITE, clear, rotate

SEGMENT_LENGTH = 5
STEP_DELAY = 0.02  # seconds per step; one lap is NUM_PIXELS steps


def white_circle():
    """Move the segment one full lap, one pixel per step."""
    for start in range(NUM_PIXELS):
        pixels[(start - 1) % NUM_PIXELS] = OFF
        pixels[(start + SEGMENT_LENGTH - 1) % NUM_PIXELS] = WHITE
        pixels.show()
        sleep(STEP_DELAY)


if __name__ == "__main__":
    clear()
    rotate([white_circle], shuffle=False)
