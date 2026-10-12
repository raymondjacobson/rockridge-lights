# RockridgeLights

400 RGB LEDs around the front of the house, driven from a Raspberry Pi (data on GPIO18).

## Control panel

`panel.py` is a web control panel. On the Pi it starts at boot (from the `pi` user's crontab) and runs at http://raspberrypi.local:8080, so you can open it from a laptop or phone on the home network.

- Pick any show, or a single animation in it, and it plays in the browser preview (a loop of all 400 lights) with its sound in the browser. Nothing touches the real lights.
- **Send to lights** plays the preview's pick on the strip, with sound on the Bluetooth speaker. Any show started by hand (`nohup python ...`) is stopped first. The lights keep playing it while you preview something else; **Turn off** stops them.
- On the lights, the schedule (on by default) keeps them dark outside the evening window.
- Settings has brightness, speaker volume, the Bluetooth speaker, and the preview's layout (where light 1 is and which way the strip runs).

The lights and the preview each run in their own `show.py` process, so switching one never disturbs the other, and a stuck show can always be stopped. The shows the panel offers are listed in `programs.py`.

The panel remembers what's on the lights in `panel_state.json`, so after a reboot it picks up where it left off. To run it by hand: `nohup python panel.py > panel.log 2>&1 &`. On a laptop, `python3 panel.py` previews only (it needs flask, numpy, and ffmpeg).

## Running a show without the panel

Each holiday is a standalone script in the repo root. Run it on the Pi with:

```
cd ~/rockridge-lights
nohup python halloween26.py &
```

To stop it, use `ps aux | grep python` to find the process, then `kill <pid>`. The lights turn off when it exits.

`python test_white.py` sends a short white segment around the whole strip, which is handy for checking the wiring.

## Writing a show

`lights.py` holds the shared strip setup (`pixels`, `NUM_PIXELS`, brightness, the sunset schedule) and `rotate()`, which plays each animation for 30 seconds in shuffled order, forever. A show only has to define its animations:

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

Colors are `(R, G, B)`. To make a show appear in the control panel, add it to `PROGRAMS` in `programs.py`.

## Sound

`halloween_audio.py` is the Halloween show with sound. It plays soundscapes from `sounds/ambience/` (owls, thunderstorms, wolves, ravens, creaking doors, wind, bells), each with its own lights, and after every few it plays a song from `sounds/music/` with one of the music visualizers.

`audio.py` analyzes each track once and caches the results in `sounds/.cache/`: loudness, eight frequency bands, and onsets. Animations can then react to the music, and even see what's coming. The thunderstorm, for example, flashes lightning just before each thunderclap.

- Tracks are matched to scenes by words in their file names: `owl`, `thunder`/`storm`, `wolf`, `crow`/`raven`, `door`/`creak`, `wind`, `bell`. Other files get a generic glow.
- Add songs through the panel's upload form, or copy them into `sounds/music/`.
- The audio files themselves aren't in git (they're large, and uploaded songs may be copyrighted). `sounds/credits.json` lists where each bundled one came from and its license.

On the lights, sound plays through PulseAudio on the paired Bluetooth speaker (a WONDERBOOM 2). While the panel is on the lights, it reconnects the speaker when it drops. Bluetooth plays a little late; the panel's "Sound delay" setting shifts the lights to match.

## Layout

- `halloween_audio.py`, `halloween26.py`, `xmas25.py`, `test_white.py`: current shows
- `panel.py`, `show.py`, `programs.py`, `web/`: the control panel
- `lights.py`, `audio.py`: shared strip and sound code
- `strip_map.py`: diagnostic that lights the strip in blocks of 100
- `archive/`: past seasons' scripts. They're self-contained and still run with `python archive/<name>.py`, but assume 500 lights.
- `index.py`, `lib/`, `songs/`: the original 2021 tweet-controlled sequences and audio visualizer. They're no longer used (the Twitter polling is dead), and they use their own strip setup in `lib/config.py`.
