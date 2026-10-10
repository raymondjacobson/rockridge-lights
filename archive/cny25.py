import board
import neopixel
from time import sleep
import random
import time
import math
import time
import itertools


NUM_PIXELS = 500

pixels = neopixel.NeoPixel(
    board.D18,
    NUM_PIXELS,
    pixel_order=neopixel.RGB,
    auto_write=False,
    brightness=0.4
)

# Halloween colors
orange = (255, 85, 0)
green = (0, 255, 60)
purple = (128, 0, 128)
dark_red = (139, 0, 0)
colors = [orange, green, purple, dark_red]

def flowing_red_waves():
    """Create flowing red waves with yellow-gold sparkles."""
    t = 0  # Time variable for animation
    while True:
        for i in range(NUM_PIXELS):
            # Calculate wave brightness
            wave = (1 + math.sin((i + t) * 0.1)) * 0.5
            intensity = int(255 * wave)

            # Assign red as the base color
            if random.random() > 0.8:  # 20% chance for yellow-gold sparkle
                color = (intensity, int(intensity * 0.8), 0)  # Yellow-gold
            else:
                color = (intensity, 0, 0)  # Red

            pixels[i] = color

        pixels.show()
        t += 1
        sleep(0.05)  # Smooth animation


def golden_sparkles():
    """Create a red background with random golden sparkles."""
    while True:
        for i in range(NUM_PIXELS):
            # Red as the default color
            pixels[i] = (255, 0, 0)  # Bright red
            
            # Randomly add golden sparkles
            if random.random() > 0.9:  # 10% chance for sparkle
                intensity = random.randint(150, 255)
                pixels[i] = (intensity, int(intensity * 0.8), 0)  # Yellow-gold sparkle

        pixels.show()
        sleep(0.1)  # Sparkle flicker timing


def alternating_bands():
    """Create alternating bands of red and yellow-gold."""
    t = 0  # Time variable for animation
    band_width = 10  # Width of each band

    while True:
        for i in range(NUM_PIXELS):
            if (i + t) // band_width % 2 == 0:
                pixels[i] = (255, 0, 0)  # Red band
            else:
                pixels[i] = (245, 182, 30)  # Yellow-gold band

        pixels.show()
        t += 1
        sleep(0.1)  # Scrolling speed


def dimming_red_glow():
    """Red lights slowly dim to zero and pop back to full brightness."""
    duration = 30  # Total time to dim in seconds
    steps = int(duration / 0.1)  # Number of steps for smooth dimming
    while True:
        # Dim from full brightness to off
        for step in range(steps):
            intensity = int(255 * (1 - step / steps))  # Linearly reduce brightness
            for i in range(NUM_PIXELS):
                pixels[i] = (intensity, 0, 0)  # Red with adjusted intensity
            pixels.show()
            sleep(0.1)  # Smooth transition

        # Snap back to full brightness
        for i in range(NUM_PIXELS):
            pixels[i] = (255, 0, 0)  # Full red
        pixels.show()
        sleep(0.1)  # Brief pause before restarting the cycle


def main():
    animations = [dimming_red_glow, flowing_red_waves, golden_sparkles, alternating_bands]
    animation_cycle = itertools.cycle(animations)  # Cycle through animations indefinitely

    while True:
        animation = next(animation_cycle)  # Get the next animation
        start_time = time.time()

        # Run the animation for 5 minutes
        while time.time() - start_time < 300:  # 300 seconds = 5 minutes
            animation()

if __name__ == "__main__":
    main()