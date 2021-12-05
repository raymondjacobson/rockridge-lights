import urllib.request
import urllib.parse as parse
import os
import numpy as np
import pyaudio
import wave
import youtube_dl
import board
import neopixel
import time
from lib import led

# script_dir = os.path.dirname(__file__)

SONG_DIR = './songs'
FPS = 60
AUDIO = None
STREAM = None

def get_wav_from_youtube(youtube_url):
    """
    Gets the .wav file for the audio of a youtube video
    """
    parsed_song_url = parse.urlparse(youtube_url)
    song_key = parse.parse_qs(parsed_song_url.query)['v'][0]

    outfile = f"{SONG_DIR}/{song_key}.wav"

    existing_song_files = os.listdir(SONG_DIR)
    if f"{song_key}.wav" not in existing_song_files:
        print(f"Downloading file to {outfile}")
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192'
            }],
            'postprocessor_args': [
                '-ar', '44100'
            ],
            'prefer_ffmpeg': True,
            'keepvideo': False,
            # Replace file name with the out templated extension
            # so that the youtube webm may be downloaded first
            # and then replaced as wav
            'outtmpl': outfile.replace('wav', '%(ext)s'),
            'progress_hooks': [on_progress]
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])

    print(f"Had existing file {outfile}")
    wf = wave.open(outfile, 'rb')
    return wf


def play(file, callback):
    def reader(in_data, frame_count, time_info, status):
        data = file.readframes(frame_count)
        callback(data)
        return (data, pyaudio.paContinue)

    p = pyaudio.PyAudio()
    stream = p.open(
        format=p.get_format_from_width(file.getsampwidth()),
        channels=file.getnchannels(),
        rate=file.getframerate(),
        output=True,
        frames_per_buffer=int(44100 / FPS),
        stream_callback = reader
    )

    return stream

def terminate():
    if STREAM:
        STREAM.stop_stream()
        STREAM.close()
    if AUDIO:
        AUDIO.terminate()

def on_progress(entries):
    downloaded_bytes = entries['downloaded_bytes']
    total_bytes = entries['total_bytes']
    percent_complete = downloaded_bytes * 1. / total_bytes * 1.
    led.loading(percent_complete)



