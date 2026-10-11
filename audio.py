"""Sound for the audio-reactive shows.

Tracks live in sounds/ambience/ and sounds/music/. Each one is analyzed once
(loudness, frequency bands, and onsets at 60 frames a second, cached in
sounds/.cache/), so an animation can look up what the audio is doing at any
moment, including a little way ahead:

    with audio.play(audio.pick("music")) as track:
        while not track.done:
            bass = track.level("low")      # 0..1 right now
            for strength in track.new_onsets():
                ...                        # a hit since the last call

`output` decides where the sound goes: "pi" plays it on the Pi's speaker
(the Bluetooth speaker when one is connected), "browser" leaves it to the
control panel, and "none" is silent.
"""
from pathlib import Path
import random
import subprocess
import threading
import time
import os

import numpy as np

SOUNDS = Path(__file__).resolve().parent / "sounds"
CACHE = SOUNDS / ".cache"
KINDS = ("ambience", "music")
EXTENSIONS = {".mp3", ".ogg", ".oga", ".wav", ".flac", ".m4a", ".aac", ".opus"}

SAMPLE_RATE = 24000
HOP = 400  # samples between feature frames: 60 per second
RATE = SAMPLE_RATE / HOP
WINDOW = 2048
BAND_EDGES = [30, 80, 160, 320, 640, 1300, 2600, 5200, 11000]  # Hz, eight bands

output = "pi"
volume = 80  # percent, for the Pi's speaker
latency = {"pi": 0.3, "browser": 0.1, "none": 0.0}  # seconds the sound lags the lights
listeners = []  # called with the current Playback (or None) when playback starts or stops

_lock = threading.Lock()


class Track:
    def __init__(self, path):
        self.path = path
        self.kind = path.parent.name
        self.name = path.stem
        self._features = None

    def has_word(self, *words):
        """Whether a word in the name starts with one of `words` ("howl" matches wind_howling, "owl" doesn't)."""
        return any(part.startswith(words) for part in self.name.split("_"))

    @property
    def title(self):
        return self.name.replace("_", " ").title()

    @property
    def features(self):
        if self._features is None:
            self._features = analyze(self.path)
        return self._features

    @property
    def duration(self):
        return float(self.features["duration"])

    @property
    def browser_file(self):
        """An mp3 copy that every browser can play."""
        mp3 = CACHE / (self.kind + "-" + self.name + ".mp3")
        if not mp3.exists() or mp3.stat().st_mtime < self.path.stat().st_mtime:
            CACHE.mkdir(parents=True, exist_ok=True)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(self.path), "-vn",
                            "-ac", "2", "-b:a", "160k", str(mp3)], check=True)
        return mp3


def library(kind=None):
    tracks = []
    for k in KINDS if kind is None else [kind]:
        folder = SOUNDS / k
        if folder.is_dir():
            tracks += [Track(p) for p in sorted(folder.iterdir()) if p.suffix.lower() in EXTENSIONS]
    return tracks


def find(name):
    for track in library():
        if track.name == name:
            return track
    raise KeyError(name)


def pick(kind, *keywords, avoid=()):
    """A random track of `kind` whose name has one of `keywords` (any track if none given)."""
    tracks = [t for t in library(kind) if not keywords or t.has_word(*keywords)]
    fresh = [t for t in tracks if t.name not in avoid]
    return random.choice(fresh or tracks) if tracks else None


def analyze(path):
    """Loudness, eight frequency bands and onset strength over time, all 0..1."""
    path = Path(path)
    cached = CACHE / "{}-{}-{}.npz".format(path.parent.name, path.stem, int(path.stat().st_mtime))
    if cached.exists():
        return dict(np.load(cached))

    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1",
                          "-ar", str(SAMPLE_RATE), "-f", "f32le", "-"],
                         check=True, stdout=subprocess.PIPE).stdout
    samples = np.frombuffer(raw, dtype=np.float32)
    samples = np.concatenate([np.zeros(WINDOW // 2, np.float32), samples, np.zeros(WINDOW, np.float32)])
    count = max(1, (len(samples) - WINDOW) // HOP)
    freqs = np.fft.rfftfreq(WINDOW, 1 / SAMPLE_RATE)
    window = np.hanning(WINDOW).astype(np.float32)
    bins = [(freqs >= lo) & (freqs < hi) for lo, hi in zip(BAND_EDGES, BAND_EDGES[1:])]

    bands = np.zeros((count, len(bins)), np.float32)
    loud = np.zeros(count, np.float32)
    flux = np.zeros(count, np.float32)
    low_flux = np.zeros(count, np.float32)
    previous = None
    for start in range(0, count, 1000):  # in chunks to keep memory low on the Pi
        idx = np.arange(start, min(count, start + 1000))
        frames = samples[idx[:, None] * HOP + np.arange(WINDOW)]
        loud[idx] = np.sqrt(np.mean(frames ** 2, axis=1))
        power = np.abs(np.fft.rfft(frames * window, axis=1)) ** 2
        for b, mask in enumerate(bins):
            bands[idx, b] = np.sqrt(power[:, mask].mean(axis=1))
        logs = np.log1p(np.sqrt(power) * 10)
        stacked = logs if previous is None else np.vstack([previous, logs])
        rise = np.maximum(0, np.diff(stacked, axis=0))
        if previous is None:
            rise = np.vstack([np.zeros_like(logs[:1]), rise])
        flux[idx] = rise.sum(axis=1)
        low_flux[idx] = rise[:, freqs < 200].sum(axis=1)
        previous = logs[-1:]

    def scale(values):
        """Decibels, stretched so the track's quiet floor is 0 and its loud parts are 1."""
        db = 20 * np.log10(values + 1e-7)
        lo, hi = np.percentile(db, 15), np.percentile(db, 99.5)
        return np.clip((db - lo) / max(hi - lo, 1e-3), 0, 1).astype(np.float32)

    def onsets(strength):
        """Peaks that stand out from the last second's average, at least 0.12 s apart."""
        strength = strength / max(np.percentile(strength, 99.5), 1e-6)
        k = int(RATE)
        average = np.convolve(np.pad(strength, (k // 2, k - k // 2 - 1), mode="edge"),
                             np.ones(k) / k, mode="valid")
        peak = (strength > average + 0.15) & (strength >= np.roll(strength, 1)) & (strength >= np.roll(strength, -1))
        times, values, last = [], [], -1.0
        for i in np.flatnonzero(peak):
            if i / RATE - last >= 0.12:
                times.append(i / RATE)
                values.append(min(1.0, strength[i] - average[i]))
                last = i / RATE
        return np.array(times, np.float32), np.array(values, np.float32)

    onset_times, onset_strengths = onsets(flux)
    low_times, low_strengths = onsets(low_flux)
    features = {
        "duration": np.float32(len(raw) / 4 / SAMPLE_RATE),
        "loud": scale(loud),
        "bands": np.stack([scale(bands[:, b]) for b in range(len(bins))], axis=1),
        "onset_times": onset_times, "onset_strengths": onset_strengths,
        "low_onset_times": low_times, "low_onset_strengths": low_strengths,
    }
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez(cached, **features)
    return features


def rises(values, high=0.6, low=0.35, gap=1.0, smooth=0.15):
    """Times when `values` (a 0..1 feature over time) climbs past `high`.

    It has to drop below `low` again before the next one counts, so one
    long rumble or hoot is a single event.
    """
    k = max(1, int(RATE * smooth))
    values = np.convolve(values, np.ones(k) / k, mode="same")
    times, armed, last = [], True, -gap
    for i, level in enumerate(values.tolist()):
        if armed and level > high and i / RATE - last >= gap:
            times.append(i / RATE)
            armed, last = False, i / RATE
        elif level < low:
            armed = True
    return times


class Cues:
    """Times in a track, each handed out once as playback reaches it."""

    def __init__(self, times):
        self.times = sorted(times)
        self.next = 0
        self.last = 0

    def due(self, t):
        if t < self.last:  # the track started over
            self.next = 0
        self.last = t
        start = self.next
        while self.next < len(self.times) and self.times[self.next] <= t:
            self.next += 1
        return self.times[start:self.next]


def _bluetooth_sink():
    try:
        sinks = subprocess.run(["pactl", "list", "short", "sinks"], stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, universal_newlines=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    for line in sinks.splitlines():
        if "bluez" in line:
            return line.split()[1]
    return None


def pulse_env():
    """Environment that reaches the desktop session's PulseAudio, even from cron or ssh."""
    env = dict(os.environ)
    runtime = "/run/user/{}".format(os.getuid())
    if os.path.isdir(runtime):
        env.setdefault("XDG_RUNTIME_DIR", runtime)
        env.setdefault("PULSE_SERVER", "unix:{}/pulse/native".format(runtime))
    return env


def set_volume(percent):
    global volume
    volume = int(percent)
    sink = _bluetooth_sink() or "@DEFAULT_SINK@"
    subprocess.run(["pactl", "set-sink-volume", sink, "{}%".format(volume)], env=pulse_env(),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


current = None  # the Playback in progress, if any


class Playback:
    """A track that is playing. `t` is where the listener is in it, in seconds."""

    def __init__(self, track):
        self.track = track
        self.features = track.features
        self.output = output
        self.process = None
        if output == "pi":
            env = pulse_env()
            sink = _bluetooth_sink()
            if sink:
                env["PULSE_SINK"] = sink
            env["SDL_AUDIODRIVER"] = "pulseaudio"
            self.process = subprocess.Popen(
                ["ffplay", "-nodisp", "-autoexit", "-loglevel", "error", str(track.path)],
                env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        self.started = time.time()
        self._last = {}

    @property
    def t(self):
        return time.time() - self.started - latency.get(self.output, 0)

    @property
    def done(self):
        return self.t >= self.track.duration

    def frame(self, t=None):
        i = int((self.t if t is None else t) * RATE)
        return min(max(i, 0), len(self.features["loud"]) - 1)

    def loudness(self, t=None):
        return float(self.features["loud"][self.frame(t)])

    def level(self, band, t=None):
        """Energy in "low", "mid", "high", or band number 0-7, 0..1."""
        bands = self.features["bands"][self.frame(t)]
        if band == "low":
            return float(bands[:3].mean())
        if band == "mid":
            return float(bands[3:6].mean())
        if band == "high":
            return float(bands[6:].mean())
        return float(bands[band])

    def bands(self, t=None):
        return self.features["bands"][self.frame(t)]

    def onsets(self, start, end, low=False):
        """(time, strength) for each onset between `start` and `end` seconds."""
        prefix = "low_onset_" if low else "onset_"
        times = self.features[prefix + "times"]
        strengths = self.features[prefix + "strengths"]
        keep = (times > start) & (times <= end)
        return list(zip(times[keep].tolist(), strengths[keep].tolist()))

    def new_onsets(self, low=False):
        """Strengths of the onsets since the last call."""
        now = self.t
        hits = self.onsets(self._last.get(low, -1.0), now, low)
        self._last[low] = now
        return [strength for _, strength in hits]

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        global current
        self.stop()
        with _lock:
            if current is self:
                current = None
        for listener in listeners:
            listener(None)


def play(track):
    """Start `track` (a Track or name) and return its Playback; use it in a with block."""
    global current
    if isinstance(track, str):
        track = find(track)
    track.features  # analyze before the clock starts
    playback = Playback(track)
    with _lock:
        current = playback
    for listener in listeners:
        listener(playback)
    return playback
