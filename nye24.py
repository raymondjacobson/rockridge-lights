import board
import math
import neopixel
import random
from datetime import datetime
from time import sleep

NUM_PIXELS = 500

pixels = neopixel.NeoPixel(
    board.D18,
    NUM_PIXELS,
    pixel_order=neopixel.RGB,
    auto_write=False,
    brightness=1
)

gold = (245, 182, 30)
silver = (100, 100, 100)
black = (0, 0, 0)

def get_random_color():
    """Generate a random color."""
    return (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

def has_passed_midnight():
    """Check if it is after midnight on New Year's Day."""
    return datetime.now() >= datetime(2025, 1, 1, 0, 0, 0)

def has_reached_cutoff():
    """Check if it is 12:15 AM on New Year's Day."""
    return datetime.now() >= datetime(2025, 1, 1, 0, 15, 0)

def festive_shimmer():
    """Shimmering gold and silver lights for a festive effect."""
    for _ in range(100):  # Run for a while
        for i in range(NUM_PIXELS):
            # Alternate gold and silver with random fading
            if random.random() > 0.5:
                intensity = random.uniform(0.5, 1.0)
                color = (
                    int(gold[0] * intensity),
                    int(gold[1] * intensity),
                    int(gold[2] * intensity),
                )
            else:
                intensity = random.uniform(0.5, 1.0)
                color = (
                    int(silver[0] * intensity),
                    int(silver[1] * intensity),
                    int(silver[2] * intensity),
                )
            pixels[i] = color

        pixels.show()
        sleep(0.1)

def fill_from_ends_to_middle(progress):
    """Fill lights from both ends toward the middle based on progress (0 to 1)."""
    midpoint = NUM_PIXELS // 2
    fill_length = int(progress * midpoint)
    
    for i in range(fill_length):
        pixels[i] = gold if i % 2 == 0 else silver
        pixels[NUM_PIXELS - i - 1] = gold if i % 2 == 0 else silver
    
    # Turn off remaining pixels
    for i in range(fill_length, midpoint):
        pixels[i] = black
        pixels[NUM_PIXELS - i - 1] = black
    
    pixels.show()

def midnight_animation():
    """Fun animation at midnight."""
    direction = 1  # Start moving forward
    position = 0

    while not has_reached_cutoff():
        for i in range(NUM_PIXELS):
            pixels[i] = get_random_color() if (i + position) % 10 < 5 else black
        pixels.show()

        # Move the position back and forth
        position += direction
        if position == NUM_PIXELS or position == 0:
            direction *= -1  # Reverse direction
        sleep(0.05)

    # Turn off lights at cutoff
    pixels.fill(black)
    pixels.show()

def main():
    while True:
        now = datetime.now()

        if has_passed_midnight():
            midnight_animation()
            return  # Exit after the animation ends at 12:15 AM
        elif now >= datetime(2024, 12, 31, 22, 0, 0):  # Start gradual fill at 10:00 PM
            # Calculate progress as a percentage of time from 10:00 PM to midnight
            seconds_since_start = (now - datetime(2024, 12, 31, 22, 0, 0)).total_seconds()
            total_seconds = (datetime(2025, 1, 1, 0, 0, 0) - datetime(2024, 12, 31, 22, 0, 0)).total_seconds()
            progress = seconds_since_start / total_seconds
            fill_from_ends_to_middle(progress)
        elif now >= datetime(2024, 12, 31, 19, 0, 0):  # Festive shimmer from 7:00 PM to 10:00 PM
            festive_shimmer()
        else:
            # Lights off before 7:00 PM
            pixels.fill(black)
            pixels.show()
        sleep(0.1)

if __name__ == "__main__":
    main()
