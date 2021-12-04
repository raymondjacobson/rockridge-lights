import board
import neopixel

pixel = neopixel.NeoPixel(board.D12, 50, pixel_order=neopixel.GRB)
pixel.fill((0, 0, 0))
