import urllib.request
import urllib.parse as parse
import os
import numpy as np
import pyaudio
import wave
from pydub import AudioSegment
from pydub.playback import play
import youtube_dl

SONG_DIR = './songs'
CHUNK = 4096

def on_progress(entries):
	downloaded_bytes = entries.downloaded_bytes
	total_bytes = entries.total_bytes
	percent_complete = downloaded_bytes * 1. / total_bytes * 1.
	print(percent_complete)

song_url = 'https://www.youtube.com/watch?v=ftSUchAdVTE'
parsed_song_url = parse.urlparse(song_url)
song_key = parse.parse_qs(parsed_song_url.query)['v'][0]

outfile = f"{SONG_DIR}/{song_key}.wav"

existing_song_files = os.listdir(SONG_DIR)

if f"{song_key}.wav" not in existing_song_files:

	print(f"downloading file to {outfile}")

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
		'outtmpl': outfile.replace('wav', '%(ext)s')
	}


	with youtube_dl.YoutubeDL(ydl_opts) as ydl:
		ydl.download([song_url])


song = AudioSegment.from_wav(outfile)
play(song)

"""
wf = wave.open(outfile, 'rb')
p = pyaudio.PyAudio()
stream = p.open(
	format=p.get_format_from_width(wf.getsampwidth()),
	channels=wf.getnchannels(),
	rate=wf.getframerate(),
	output=True
)

data = wf.readframes(CHUNK)
while data != '':
	stream.write(data)
	data = wf.readframes(CHUNK)
	human_data = np.frombuffer(data, dtype=np.int16)
	peak = np.average(np.abs(human_data)) * 2
	print(peak)

stream.close()
p.terminate()
"""
