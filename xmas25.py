from time import sleep
import random
import math

from lights import pixels, NUM_PIXELS, rotate


def twinkling_snowfall():
    """Simulate a gentle snowfall with random twinkling lights."""
    for _ in range(100):  # Number of snowfall cycles
        for i in range(NUM_PIXELS):
            if random.random() > 0.8:  # 20% chance of a pixel twinkling
                pixels[i] = (255, 255, 255)  # White for snow
            else:
                pixels[i] = (0, 0, 0)  # Clear the rest
        pixels.show()
        sleep(0.1)  # Gentle snowfall speed


def candy_cane_stripes():
    """Create scrolling red and white candy cane stripes."""
    stripe_width = 5  # Width of each stripe
    for offset in range(NUM_PIXELS):  # Scroll through the strip
        for i in range(NUM_PIXELS):
            if (i + offset) // stripe_width % 2 == 0:
                pixels[i] = (255, 0, 0)  # Red stripe
            else:
                pixels[i] = (255, 255, 255)  # White stripe
        pixels.show()
        sleep(0.05)  # Scrolling speed

def christmas_tree_glow():
    """Simulate a glowing Christmas tree with twinkling red ornaments."""
    for _ in range(100):  # Duration of the glow
        for i in range(NUM_PIXELS):
            # Green base with random red twinkles
            if random.random() > 0.9:  # 10% chance of a red ornament
                pixels[i] = (255, 0, 0)  # Red for ornaments
            else:
                pixels[i] = (0, 255, 0)  # Green for the tree
        pixels.show()
        sleep(0.1)  # Smooth glowing effect

def festive_rainbow_chase():
    """Chase a rainbow of Christmas colors down the strip."""
    colors = [(255, 0, 0), (0, 255, 0), (255, 255, 255)]  # Red, green, white
    for offset in range(NUM_PIXELS):  # Scroll through the strip
        for i in range(NUM_PIXELS):
            pixels[i] = colors[(i + offset) % len(colors)]  # Cycle colors
        pixels.show()
        sleep(0.05)  # Speed of the chase

def starry_night_twinkle():
    """Simulate a peaceful starry night with green and red stars."""
    for _ in range(100):  # Duration of the twinkle
        for i in range(NUM_PIXELS):
            if random.random() > 0.85:  # 15% chance of a star
                pixels[i] = random.choice([(0, 255, 0), (255, 0, 0)])  # Green or red star
            else:
                pixels[i] = (255, 255, 255)  # Snowy background
        pixels.show()
        sleep(0.1)  # Twinkling effect


def northern_lights_glow():
    """Simulate shifting northern lights with Christmas colors."""
    for phase in range(100):  # Total animation cycles
        for i in range(NUM_PIXELS):
            # Generate a smooth wave effect
            intensity = (1 + math.sin((i + phase) * 0.1)) / 2  # Wave formula
            color = random.choice([(255, 0, 0), (0, 255, 0), (255, 255, 255)])  # Red, green, or white
            pixels[i] = tuple(int(c * intensity) for c in color)  # Adjust intensity
        pixels.show()
        sleep(0.05)  # Smooth transition speed


def snowstorm_chaos():
    """Create a chaotic snowstorm with swirling snowflakes and random flashes."""
    for _ in range(150):  # Animation cycles
        for i in range(NUM_PIXELS):
            # Random white snowflakes with occasional flashes of color
            if random.random() > 0.8:
                pixels[i] = (255, 255, 255)  # Snowflake
            elif random.random() > 0.95:  # Rarely flash color
                pixels[i] = random.choice([(255, 0, 0), (0, 255, 0)])  # Red or green flash
            else:
                pixels[i] = (0, 0, 0)  # Clear
        pixels.show()
        sleep(0.07)  # Fast-paced, chaotic speed


def wreath_sparkle():
    """Simulate a glowing wreath with green and red sparkles."""
    center = NUM_PIXELS // 2
    for radius in range(1, NUM_PIXELS // 2, 2):  # Expand outward in circles
        for i in range(NUM_PIXELS):
            distance = abs(center - i)
            if distance <= radius:
                pixels[i] = (0, 255, 0) if random.random() > 0.5 else (255, 0, 0)  # Green or red
            else:
                pixels[i] = (0, 0, 0)  # Off
        pixels.show()
        sleep(0.1)  # Radiating speed


def gift_unwrapping():
    """Simulate a wrapped gift unwrapping with alternating colors."""
    for offset in range(NUM_PIXELS // 2):  # Expand inward from the edges
        for i in range(NUM_PIXELS):
            if i < offset or i >= NUM_PIXELS - offset:
                pixels[i] = (255, 0, 0)  # Red wrapping
            elif i == offset or i == NUM_PIXELS - offset - 1:
                pixels[i] = (0, 255, 0)  # Green unwrapping edge
            else:
                pixels[i] = (255, 255, 255)  # White interior
        pixels.show()
        sleep(0.05)  # Unwrapping speed


def fireplace_flicker():
    """Simulate a flickering fireplace with orange and red hues."""
    for _ in range(100):  # Flicker cycles
        for i in range(NUM_PIXELS):
            intensity = random.uniform(0.7, 1)  # Random flicker intensity
            pixels[i] = (
                int(255 * intensity),  # Red
                int(100 * intensity),  # Orange
                0,  # No blue
            )
        pixels.show()
        sleep(random.uniform(0.05, 0.15))  # Random flicker speed


def icicle_drips():
    """Simulate icy blue and white drips running down the strip."""
    for _ in range(100):  # Drip cycles
        for i in range(NUM_PIXELS):
            if random.random() > 0.8:  # Occasional drip
                pixels[i] = (173, 216, 230)  # Light blue for icicles
            else:
                pixels[i] = (255, 255, 255)  # Snowy white background
        pixels.show()
        sleep(0.1)  # Drip speed


def christmas_starburst():
    """Radiate light outward from random points."""
    for _ in range(20):  # Number of bursts
        center = random.randint(0, NUM_PIXELS - 1)  # Random center
        for radius in range(NUM_PIXELS // 4):  # Expand outward
            for i in range(NUM_PIXELS):
                if abs(i - center) == radius:
                    pixels[i] = random.choice([(255, 0, 0), (0, 255, 0), (255, 255, 255)])
                else:
                    pixels[i] = (0, 0, 0)
            pixels.show()
            sleep(0.05)  # Expansion speed


def candy_cane_ripple():
    """Ripple red and white rings outward from the center."""
    center = NUM_PIXELS // 2
    for radius in range(NUM_PIXELS // 2):
        for i in range(NUM_PIXELS):
            distance = abs(center - i)
            pixels[i] = (255, 0, 0) if (distance + radius) % 2 == 0 else (255, 255, 255)
        pixels.show()
        sleep(0.05)  # Ripple speed


def santas_sleigh_chase():
    """Simulate Santa's sleigh racing down the strip."""
    for start in range(NUM_PIXELS):
        for i in range(NUM_PIXELS):
            if start <= i < start + 3:  # Red sleigh
                pixels[i] = (255, 0, 0)
            elif start + 3 <= i < start + 10:  # White reindeer
                pixels[i] = (255, 255, 255)
            else:
                pixels[i] = (0, 0, 0)
        pixels.show()
        sleep(0.02)  # Speed of the sleigh


def gift_drop():
    """Simulate gifts dropping down the strip."""
    for drop in range(NUM_PIXELS // 10):
        for i in range(NUM_PIXELS):
            if drop <= i < drop + 10:  # Gift block
                pixels[i] = random.choice([(255, 0, 0), (0, 255, 0)])
            else:
                pixels[i] = (0, 0, 0)
        pixels.show()
        sleep(0.05)  # Dropping speed


def snowflake_explosion():
    """Create clusters of snowflakes exploding randomly."""
    for _ in range(20):
        center = random.randint(0, NUM_PIXELS - 1)  # Random center
        for i in range(NUM_PIXELS):
            if abs(i - center) <= random.randint(1, 5):  # Small cluster
                pixels[i] = (255, 255, 255)
            else:
                pixels[i] = (0, 0, 0)
        pixels.show()
        sleep(0.1)  # Explosive speed


def festive_fireworks():
    """Simulate colorful fireworks shooting up and bursting."""
    for _ in range(10):  # Number of fireworks
        height = random.randint(0, NUM_PIXELS - 1)  # Random burst height
        for step in range(height):
            for i in range(NUM_PIXELS):
                pixels[i] = (255, 255, 255) if i == step else (0, 0, 0)
            pixels.show()
            sleep(0.02)  # Shooting up
        for i in range(NUM_PIXELS):
            if abs(i - height) < 5:  # Burst range
                pixels[i] = random.choice([(255, 0, 0), (0, 255, 0), (255, 255, 255)])
        pixels.show()
        sleep(0.1)  # Burst duration


def stocking_fill():
    """Simulate a stocking filling upward."""
    for level in range(NUM_PIXELS // 10):  # Filling levels
        for i in range(NUM_PIXELS):
            if i < level * 10:  # Filled area
                pixels[i] = random.choice([(255, 0, 0), (0, 255, 0), (255, 255, 255)])
            else:
                pixels[i] = (0, 0, 0)
        pixels.show()
        sleep(0.1)  # Filling speed


def icicle_shimmer():
    """Simulate shimmering icicles flowing."""
    for offset in range(NUM_PIXELS):
        for i in range(NUM_PIXELS):
            pixels[i] = (173, 216, 230) if (i + offset) % 2 == 0 else (255, 255, 255)
        pixels.show()
        sleep(0.05)  # Shimmering speed


def christmas_tree_sparkle():
    """Simulate decorations sparkling on a tree."""
    for _ in range(50):
        for i in range(NUM_PIXELS):
            if random.random() > 0.9:
                pixels[i] = random.choice([(255, 0, 0), (0, 255, 0), (255, 215, 0)])  # Red, green, gold
            else:
                pixels[i] = (0, 0, 0)
        pixels.show()
        sleep(0.1)  # Sparkling speed


def elf_dance():
    """Simulate elves dancing down the strip."""
    for step in range(NUM_PIXELS // 5):
        for i in range(NUM_PIXELS):
            if step <= i < step + 5:  # Cluster of lights
                pixels[i] = random.choice([(0, 255, 0), (255, 0, 0)])  # Green or red
            else:
                pixels[i] = (0, 0, 0)
        pixels.show()
        sleep(0.1)  # Dancing rhythm


def candy_cane_spiral():
    """Create a spiraling red and white candy cane effect."""
    stripe_width = 5  # Width of each spiral segment
    for offset in range(NUM_PIXELS):  # Scroll through the strip
        for i in range(NUM_PIXELS):
            if (i + offset) // stripe_width % 2 == 0:
                pixels[i] = (255, 0, 0)  # Red stripe
            else:
                pixels[i] = (255, 255, 255)  # White stripe
        pixels.show()
        sleep(0.03)  # Spiral speed


def bell_chime_animation():
    """Simulate the motion of a swinging bell."""
    center = NUM_PIXELS // 2
    for swing in range(NUM_PIXELS // 4):
        for i in range(NUM_PIXELS):
            distance = abs(center - i)
            if distance == swing or distance == swing + 1:  # Swing effect
                pixels[i] = (255, 255, 0)  # Golden bell
            else:
                pixels[i] = (0, 0, 0)
        pixels.show()
        sleep(0.05)  # Swing speed


def snowball_toss():
    """Simulate snowballs arcing down the strip."""
    for toss in range(NUM_PIXELS // 10):
        for i in range(NUM_PIXELS):
            if toss <= i < toss + 10:
                pixels[i] = (255, 255, 255)  # Snowball
            else:
                pixels[i] = (0, 0, 0)
        pixels.show()
        sleep(0.05)  # Toss speed


def winter_aurora():
    """Simulate slow waves of green and blue auroras."""
    for phase in range(100):
        for i in range(NUM_PIXELS):
            intensity = (1 + math.sin((i + phase) * 0.1)) / 2  # Wave formula
            pixels[i] = (
                int(0 * intensity),
                int(255 * intensity),
                int(255 * (1 - intensity)),  # Blend green and blue
            )
        pixels.show()
        sleep(0.05)  # Wave speed


def holiday_countdown():
    """Simulate a countdown timer effect."""
    for i in range(NUM_PIXELS):
        if i % 3 == 0:
            pixels[i] = (255, 0, 0)  # Red
        elif i % 3 == 1:
            pixels[i] = (0, 255, 0)  # Green
        else:
            pixels[i] = (255, 255, 255)  # White
        pixels.show()
        sleep(0.02)  # Countdown spe


def polar_express():
    """Simulate a train moving down the strip."""
    for start in range(NUM_PIXELS):
        for i in range(NUM_PIXELS):
            if i == start:
                pixels[i] = (255, 255, 255)  # Headlight
            elif start - 5 < i < start:  # Train trail
                pixels[i] = (255, 0, 0)  # Red train car
            else:
                pixels[i] = (0, 0, 0)
        pixels.show()
        sleep(0.02)


def peppermint_spin():
    """Create a peppermint spinning effect."""
    for spin in range(100):
        for i in range(NUM_PIXELS):
            pixels[i] = (255, 0, 0) if (i + spin) % 2 == 0 else (255, 255, 255)  # Red and white
        pixels.show()
        sleep(0.02)  # Spinning speed


def fireplace_ember_glow():
    """Simulate flickering embers."""
    for _ in range(100):
        for i in range(NUM_PIXELS):
            intensity = random.uniform(0.7, 1)
            pixels[i] = (
                int(255 * intensity),  # Red
                int(100 * intensity),  # Orange
                0,  # No blue
            )
        pixels.show()
        sleep(random.uniform(0.05, 0.15))  # Flicker speed


def ornament_swing():
    """Simulate ornaments swinging back and forth."""
    for swing in range(NUM_PIXELS // 4):
        for i in range(NUM_PIXELS):
            if i % 10 == swing or i % 10 == swing + 1:
                pixels[i] = random.choice([(255, 0, 0), (0, 255, 0)])  # Red or green ornament
            else:
                pixels[i] = (0, 0, 0)
        pixels.show()
        sleep(0.05)  # Swing speed


def holiday_garland_sweep():
    """Simulate garland sweeping with berries."""
    for sweep in range(NUM_PIXELS):
        for i in range(NUM_PIXELS):
            if i == sweep:
                pixels[i] = (0, 255, 0)  # Garland
            elif random.random() > 0.9:
                pixels[i] = random.choice([(255, 0, 0), (255, 255, 255)])  # Red or white berry
            else:
                pixels[i] = (0, 0, 0)
        pixels.show()
        sleep(0.03)  # Sweep speed


def christmas_snowstorm_symphony():
    """Create a swirling, musical snowstorm with dynamic patterns."""
    t = 0  # Time variable for animation
    while t < 500:  # Run for 500 frames (adjustable for duration)
        for i in range(NUM_PIXELS):
            # Calculate position-based brightness for swirling effect
            swirl = math.sin((i + t) * 0.1) + math.cos((i - t) * 0.15)
            brightness = (1 + math.sin(t * 0.1)) * 0.5  # Dynamic fade in/out
            intensity = swirl * brightness  # Combined intensity effect
            
            # Clamp intensity to ensure it is within 0-255 range
            scaled_intensity = int(min(max(255 * intensity / 2, 0), 255))

            # Choose a color dynamically (red, green, or white) based on position and time
            if (i + t) % 3 == 0:
                color = (scaled_intensity, 0, 0)  # Red
            elif (i + t) % 3 == 1:
                color = (0, scaled_intensity, 0)  # Green
            else:
                color = (scaled_intensity, scaled_intensity, scaled_intensity)  # White (snow)

            # Set the pixel's color
            pixels[i] = color if scaled_intensity > 10 else (0, 0, 0)  # Turn off for very low intensity

        # Show the updated frame
        pixels.show()

        # Increment time for the next frame
        t += 1
        sleep(0.02)  # High FPS (50 frames per second)


def swirling_blizzard():
    """Create an icy blue and white blizzard that crescendos and mellows."""
    t = 0  # Time variable for animation
    crescendo = True  # Tracks whether the blizzard is growing or settling
    max_intensity = 2.0  # Max brightness multiplier for crescendo

    while t < 600:  # Run for 600 frames
        for i in range(NUM_PIXELS):
            # Calculate position-based brightness for swirling effect
            swirl = math.sin((i + t) * 0.1) + math.cos((i - t) * 0.15)
            brightness = (1 + math.sin(t * 0.05)) * 0.5  # Dynamic fade in/out
            intensity = swirl * brightness * (max_intensity if crescendo else 0.5)
            
            # Clamp and scale intensity
            scaled_intensity = int(min(max(255 * intensity / 2, 0), 255))

            # Alternate icy blue and white
            if (i + t) % 2 == 0:
                color = (0, int(scaled_intensity * 0.8), scaled_intensity)  # Blue-white
            else:
                color = (scaled_intensity, scaled_intensity, scaled_intensity)  # Pure white

            # Set pixel color
            pixels[i] = color if scaled_intensity > 10 else (0, 0, 0)

        # Show the frame
        pixels.show()

        # Adjust crescendo dynamics
        if crescendo and t % 200 == 0:
            max_intensity -= 0.1  # Slowly reduce crescendo
            if max_intensity <= 1.0:  # Switch to mellowing
                crescendo = False

        t += 1
        sleep(0.02)  # High FPS


def fireplace_flicker_with_growth():
    """Create a warm flickering fireplace that grows and then mellows out."""
    t = 0  # Time variable for animation
    crescendo = True  # Tracks whether the fireplace is growing or settling
    max_intensity = 1.0  # Max brightness multiplier for crescendo

    while t < 600:  # Run for 600 frames
        for i in range(NUM_PIXELS):
            # Flickering effect with random brightness variation
            base_intensity = max_intensity if crescendo else 0.5
            flicker = random.uniform(0.7, 1.0) * base_intensity
            intensity = flicker * (1 + math.sin(t * 0.05)) * 0.5

            # Clamp and scale intensity
            scaled_intensity = int(min(max(255 * intensity, 0), 255))

            # Reds and oranges for the fire
            pixels[i] = (scaled_intensity, int(scaled_intensity * 0.4), 0)

        # Show the frame
        pixels.show()

        # Adjust crescendo dynamics
        if crescendo and t % 200 == 0:
            max_intensity += 0.1  # Gradually increase warmth
            if max_intensity >= 2.0:  # Peak warmth
                crescendo = False

        t += 1
        sleep(0.02)  # High FPS


def candycane_growth():
    """Simulate candy canes growing and shrinking like a magical effect."""
    t = 0  # Time variable for animation
    growing = True  # Tracks whether the candycanes are growing or shrinking
    max_width = 1  # Tracks the growth/shrink width

    while t < 600:  # Run for 600 frames
        for i in range(NUM_PIXELS):
            # Stripe effect with dynamic growth width
            if (i // max_width) % 2 == 0:
                color = (255, 0, 0)  # Red stripe
            else:
                color = (255, 255, 255)  # White stripe

            # Only display within the current growth size
            pixels[i] = color if abs(i - NUM_PIXELS // 2) < max_width * 10 else (0, 0, 0)

        # Show the frame
        pixels.show()

        # Adjust growth/shrink dynamics
        if growing:
            max_width += 1
            if max_width >= NUM_PIXELS // 20:  # Peak growth
                growing = False
        else:
            max_width -= 1
            if max_width <= 1:  # Back to the start
                growing = True

        t += 1
        sleep(0.02)  # High FPS


ANIMATIONS = [
    swirling_blizzard,
    fireplace_flicker_with_growth,
    candycane_growth,
    christmas_snowstorm_symphony,
    twinkling_snowfall,
    candy_cane_stripes,
    christmas_tree_glow,
    northern_lights_glow,
    snowstorm_chaos,
    wreath_sparkle,
    gift_unwrapping,
    fireplace_flicker,
    icicle_drips,
    starry_night_twinkle,
    candy_cane_spiral,
    bell_chime_animation,
    snowball_toss,
    winter_aurora,
    holiday_countdown,
    polar_express,
    # peppermint_spin,
    fireplace_ember_glow,
    ornament_swing,
    holiday_garland_sweep,
]

if __name__ == "__main__":
    rotate(ANIMATIONS)
