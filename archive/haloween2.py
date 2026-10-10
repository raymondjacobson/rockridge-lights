import board
import neopixel
from time import sleep
import random
import time

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

# Function to create a candle-like flicker effect
def flicker_color(color, intensity=0.8):
    return tuple(int(c * intensity * random.uniform(0.5, 1)) for c in color)

def candle_flicker():
    """Simulate candle flickering effect with occasional color changes"""
    start_time = time.time()
    while time.time() - start_time < random.uniform(5, 10):  # Flicker for 5-10 seconds
        color = random.choice([dark_red, orange, purple])
        for i in range(NUM_PIXELS):
            pixels[i] = flicker_color(color)
        pixels.show()
        sleep(random.uniform(0.05, 0.15))  # Flickering speed

def spooky_random_pattern():
    """A random spooky pattern that will scare kids"""
    duration = random.uniform(3, 5)  # Pattern lasts 3-5 seconds
    start_time = time.time()
    while time.time() - start_time < duration:
        for i in range(NUM_PIXELS):
            pixels[i] = random.choice(colors) if random.random() > 0.7 else (0, 0, 0)
        pixels.show()
        sleep(0.05)  # Creates a chaotic, eerie effect

def quick_run_down_strip():
    """Run multiple quick, wider flashes of lights down the strip"""
    runners = [0, NUM_PIXELS // 4, NUM_PIXELS // 2, (3 * NUM_PIXELS) // 4]  # Starting points for each runner
    colors_for_runners = [random.choice(colors) for _ in range(4)]  # Random color for each runner

    for _ in range(NUM_PIXELS // 2):  # Number of steps for each runner to move down
        for idx, start in enumerate(runners):
            color = colors_for_runners[idx]
            position = (start + _) % NUM_PIXELS  # Move each runner down the strip

            # Set color for the current runner's position
            for width in range(3):  # Make the runner wider
                if position + width < NUM_PIXELS:
                    pixels[position + width] = color

            # Clear previous pixels to create a trailing effect
            trailing_position = (position - 3) % NUM_PIXELS
            for width in range(3):
                if trailing_position + width < NUM_PIXELS:
                    pixels[trailing_position + width] = (0, 0, 0)

        pixels.show()
        sleep(0.005)  # Faster pace

    # Clear all runners at the end of the run
    for i in range(NUM_PIXELS):
        pixels[i] = (0, 0, 0)
    pixels.show()


def lightning_strike():
    """Simulate random lightning strikes across the strip"""
    strike_duration = random.uniform(0.1, 0.3)  # Quick flash for a lightning effect
    for _ in range(random.randint(1, 3)):  # 1 to 3 quick strikes per sequence
        color = (255, 255, 255)  # Bright white for lightning
        for i in range(NUM_PIXELS):
            pixels[i] = color
        pixels.show()
        sleep(strike_duration)  # Quick flash

        # Dim down the strip quickly
        for i in range(NUM_PIXELS):
            pixels[i] = (int(color[0] * 0.1), int(color[1] * 0.1), int(color[2] * 0.1))
        pixels.show()
        sleep(0.1)  # Brief pause between strikes

def chasing_eyes():
    """Create two 'eyes' moving down the strip"""
    eye_color = (255, 0, 0)  # Red color for eerie eyes
    gap_between_eyes = 5  # Distance between the eyes
    eye_speed = 0.05  # Speed of the eye movement

    for position in range(0, NUM_PIXELS - gap_between_eyes, 2):
        # Set the positions for two eyes
        pixels[position] = eye_color
        if position + gap_between_eyes < NUM_PIXELS:
            pixels[position + gap_between_eyes] = eye_color

        # Display and pause
        pixels.show()
        sleep(eye_speed)

        # Turn off the eyes as they move forward
        pixels[position] = (0, 0, 0)
        if position + gap_between_eyes < NUM_PIXELS:
            pixels[position + gap_between_eyes] = (0, 0, 0)

    # Clear the strip after the eyes finish chasing
    pixels.fill((0, 0, 0))
    pixels.show()

def split_colors():
    """Split the strip into two colors, switching color pairs every few seconds"""
    duration = random.uniform(3, 6)  # Pattern lasts 3-6 seconds
    color_pair = random.sample(colors, 2)
    while duration > 0:
        for i in range(NUM_PIXELS):
            if i < NUM_PIXELS // 2:
                pixels[i] = color_pair[0]  # First half
            else:
                pixels[i] = color_pair[1]  # Second half
        pixels.show()
        sleep(2)  # Switch every 2 seconds
        duration -= 2  # Countdown for switching

def color_pulse_waves():
    """Create pulsing waves of color outward from the center of the strip"""
    pulse_colors = [dark_red, purple, orange]  # Halloween colors to pulse
    center = NUM_PIXELS // 2

    for color in pulse_colors:
        # Pulse out from the center
        for offset in range(center):
            # Set pixels moving outward from the center
            if center + offset < NUM_PIXELS:
                pixels[center + offset] = color
            if center - offset >= 0:
                pixels[center - offset] = color
            pixels.show()
            sleep(0.02)  # Speed of the pulse

        # Clear the strip after each pulse wave
        pixels.fill((0, 0, 0))
        pixels.show()
        sleep(0.5)  # Brief pause between pulses

def main():
    while True:
        # Run each animation for 30 seconds
        start_time = time.time()
        
        # Candle flicker effect
        while time.time() - start_time < 30:
            candle_flicker()

        # Quick run down the strip
        start_time = time.time()
        while time.time() - start_time < 30:
            quick_run_down_strip()

        # Spooky random pattern
        start_time = time.time()
        while time.time() - start_time < 30:
            spooky_random_pattern()

        # Split colors effect
        start_time = time.time()
        while time.time() - start_time < 30:
            split_colors()

        # Lightning strike flash for variety
        start_time = time.time()
        while time.time() - start_time < 30:
            lightning_strike()

        # Chasing eyes for added eeriness
        start_time = time.time()
        while time.time() - start_time < 30:
            chasing_eyes()

        # Color pulse waves for a heartbeat effect
        start_time = time.time()
        while time.time() - start_time < 30:
            color_pulse_waves()

if __name__ == "__main__":
    main()
