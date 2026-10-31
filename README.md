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

## On the internet

The same panel is also at https://rockridge-lights.monophonic.workers.dev, behind a password, so it works from a phone anywhere. It's a Cloudflare Worker (`cloud/`, in Ray's own Cloudflare account, next to Frog's) that serves `web/index.html`; the panel on the Pi keeps a WebSocket open to it (`cloud.py`) and answers the page's calls over it. The Pi only ever connects out, so nothing at home is opened up.

- The page streams the lights and the preview from the Pi only while someone has it open.
- A sound is copied to the Worker the first time it's played there, so later plays don't wait on the Pi's upload.
- If the Pi is off or offline, the page says so and catches up when it's back.

Setting it up, once (Ray runs these from a checkout on the Mac):

```
./scripts/deploy-cloud.sh                                  # the Worker
./scripts/deploy-pi.sh                                     # the code and websocket-client on the Pi
(cd cloud && npx wrangler secret put LIGHTS_PASSWORD)      # the panel password
./scripts/pair-device.sh                                   # a device token for the Pi; restarts the panel
```

The Pi keeps its address and token in `~/.config/rockridge-lights/cloud.env` (never in git). The panel logs the link as `cloud: ...` lines in `panel.log`; `npx wrangler tail rockridge-lights` (in `cloud/`) shows the Worker's side.

To try it all on a laptop: put test values for `LIGHTS_PASSWORD` and `LIGHTS_DEVICE_TOKEN` in `cloud/.dev.vars`, run `npx wrangler dev` in `cloud/`, and start the panel with those two plus `LIGHTS_CLOUD_URL=ws://127.0.0.1:8787/device` in its environment.

## The Grim Reaper (Frog) and the lights

Frog's Grim Reaper next door can change the lights when someone asks: "laugh" makes it cackle while the house flickers with each "ha", and "make the lights red, like blood" puts a look on for a minute. Its brain (the `frog-brain` Worker) reaches this Worker's `LightsControl` over a service binding, a private link with no URL, and the panel does the rest (`/api/frog` routes in `panel.py`):

- **Looks**: any animation from Halloween reds, Christmas 2025 or Effects, or an effect made to order (`effects.py`: a kind, colors, a speed). A look lasts a minute, then the lights go back to what was last sent from the panel. The panel says "The Grim Reaper's pick" meanwhile.
- **Moments** (`moments.py`): a few seconds layered over whatever is playing, without restarting it: the cackle, lightning, a pulse, a flash.
- **Their own hours**: while the lights are off, asleep (outside the schedule) or started by hand, Frog's requests are refused and it says so. It can never turn them on.

## Updating the Pi from another computer

Commits can be made on the Pi itself or in a clone. `./scripts/deploy-pi.sh` fast-forwards the Pi to the clone's commits (it refuses if the Pi has commits the clone doesn't), and `./scripts/restart-panel.sh` restarts the panel on the new code (the lights blink for a moment).

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

`halloween_audio.py` is the Halloween show with sound, and what a new Pi plays by default. It plays soundscapes from `sounds/ambience/`, each with its own lights, changing about every minute (`SCENE_SECONDS`). After every three it plays a Halloween reds pattern with no sound, and after two of those a whole song from `sounds/music/`. Songs get a full light show from `visualizer.py`: it finds the beats, bars and sections ahead of time and gives each section its own act (fire, serpents, shockwaves...) and palette, darker when the music is quiet and wilder when it is loud. Picking one soundscape in the panel still plays its whole track.

`audio.py` analyzes each track once and caches the results in `sounds/.cache/`: loudness, eight frequency bands, and onsets. Animations can then react to the music, and even see what's coming. The thunderstorm, for example, flashes lightning just before each thunderclap.

- Tracks are matched to scenes by words in their file names (`KEYWORDS` in `halloween_audio.py`): `owl`, `thunder`/`storm`, `wolf`, `crow`/`raven`, `door`/`creak`, `wind`, `bell`, `witch`, `monster`, `heartbeat`, `bats`, `foghorn`, and so on. Other files get a generic glow.
- Add songs through the panel's upload form, or copy them into `sounds/music/`. A song whose file name starts with `thriller` or `monster` comes up more often (`FAVORITE_SONGS`).
- The audio files themselves aren't in git (they're large, and uploaded songs may be copyrighted). `sounds/credits.json` lists where each bundled one came from and its license.

On the lights, sound plays through PulseAudio on the paired Bluetooth speaker (a WONDERBOOM 2). While the panel is on the lights, it reconnects the speaker when it drops. Bluetooth plays a little late; the panel's "Sound delay" setting shifts the lights to match.

## Layout

- `halloween_audio.py`, `halloween26.py`, `xmas25.py`, `test_white.py`: current shows
- `panel.py`, `show.py`, `programs.py`, `web/`: the control panel
- `cloud.py`, `cloud/`: the panel on the internet (the Pi's side, and the Cloudflare Worker)
- `effects.py`, `moments.py`: looks made to order and moments over a show, for Frog
- `scripts/`: deploying the Worker and the Pi, pairing them, restarting the panel
- `lights.py`, `audio.py`: shared strip and sound code
- `strip_map.py`: diagnostic that lights the strip in blocks of 100
- `archive/`: past seasons' scripts. They're self-contained and still run with `python archive/<name>.py`, but assume 500 lights.
- `index.py`, `lib/`, `songs/`: the original 2021 tweet-controlled sequences and audio visualizer. They're no longer used (the Twitter polling is dead), and they use their own strip setup in `lib/config.py`.
