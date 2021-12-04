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

pixel = neopixel.NeoPixel(board.D12, 50, pixel_order=neopixel.GRB)

SONG_DIR = './songs'
CHUNK = 1024

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
			'-ar', '48000'
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

wf = wave.open(outfile, 'rb')
print(wf.getsampwidth())

"""
import alsaaudio
periodsize=wf.getframerate() // 8
device = alsaaudio.PCM(
	channels=wf.getnchannels(),
	rate=wf.getframerate(),
	format=alsaaudio.PCM_FORMAT_S16_LE,
	periodsize=periodsize
)

data = wf.readframes(periodsize)
while data:
	device.write(data)
	data = wf.readframes(periodsize)
"""

p = pyaudio.PyAudio()

for i in range(p.get_device_count()):
	dev = p.get_device_info_by_index(i)
	print((i,dev['name'],dev['maxInputChannels']))
print(wf.getframerate())

"""
def reader(in_data, frame_count, time_info, status):
	data = wf.readframes(frame_count)
	human_data = np.frombuffer(data, dtype=np.int16)
	peak = np.average(np.abs(human_data)) * 2
	power = peak / 20000.
	print(power)
	pixel.fill((0, peak / 20000., 0))
	return (data, pyaudio.paContinue)

"""
stream = p.open(
	format=p.get_format_from_width(wf.getsampwidth()),
	channels=wf.getnchannels(),
	rate=wf.getframerate(),
	output=True,
	output_device_index=0,
	frames_per_buffer=48000,
	#stream_callback = reader
)
"""
while stream.is_active():
	time.sleep(0.1)

stream.stop_stream()
stream.close()
p.terminate()
"""


data = wf.readframes(CHUNK)
while data != '':
	stream.write(data)
	data = wf.readframes(CHUNK)

	#human_data = np.frombuffer(data, dtype=np.int16)
	#peak = np.average(np.abs(human_data)) * 2
	#power = peak / 20000.
	#pixel.fill((0, peak / 20000., 0))

stream.close()
p.terminate()


