# RockridgeLights

400 LEDs driven from a Raspberry Pi (data on GPIO18).

## Running a show

Each holiday is a standalone script in the repo root. Run it on the Pi with:

```
cd ~/rockridge-lights
nohup python xmas25.py &
```

Shows that call `rotate(..., scheduled=True)` (currently `halloween26.py`) turn on 30 minutes before sunset and off at midnight on their own, so you can leave them running. Location and timing are at the top of `lights.py`.

To stop it, use `ps aux | grep python` to find the process, then `kill <pid>`. The lights turn off when it exits.

`python test_white.py` sends a short white segment around the whole strip, which is handy for checking that the wiring is OK.

## Writing a show

`lights.py` holds the shared strip setup (`pixels`, `NUM_PIXELS`, brightness) and `rotate()`, which plays each animation for 30 seconds in shuffled order, forever. A show only has to define its animations:

```python
from time import sleep
from lights import pixels, NUM_PIXELS, rotate

def all_orange():
    pixels.fill((255, 85, 0))
    pixels.show()
    sleep(1)

if __name__ == "__main__":
    rotate([all_orange])
```

Colors are `(R, G, B)`. To change brightness for one show, set `pixels.brightness = 0.3` before calling `rotate()`.

## Layout

- `halloween26.py`, `xmas25.py`, `test_white.py`: current shows
- `archive/`: past seasons' scripts. They're self-contained and still run with `python archive/<name>.py`.
- `index.py`, `lib/`, `songs/`: the original 2021 tweet-controlled sequences and audio visualizer. They're no longer used (the Twitter polling is dead), and they use their own strip setup in `lib/config.py`.
