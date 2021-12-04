import pafy
import vlc
import time

url = "https://www.youtube.com/watch?v=ftSUchAdVTE"

video = pafy.new(url)

print(video.title)

bestaudio = video.getbestaudio()

print(video.audiostreams)
print(bestaudio.url)

equalizer = vlc.libvlc_audio_equalizer_new()

"""
player = vlc.MediaPlayer(bestaudio.url)
player.set_equalizer(equalizer)
player.play()


print(equalizer.get_preamp())


while True:
	time.sleep(1)
	print(equalizer.get_preamp())
"""
