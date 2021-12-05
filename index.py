import subprocess
import sys
import time
from lib import audio
from lib import twt
from lib import led
from lib.constants import Sequence

SEQUENCE = None
PROCESS = None
STREAM = None
LAST_TWEET_ID = None

counter = 0
while True:
    if counter % 5000 == 0:
        (new_sequence, youtube_url, last_tweet_id) = twt.poll_for_tweets(LAST_TWEET_ID)
        LAST_TWEET_ID = last_tweet_id

        if new_sequence:
            # Terminate existing sequence
            if PROCESS:
                PROCESS.terminate()
                PROCESS = None
            if STREAM:
                audio.terminate(STREAM)

            # Run a new sequence
            if new_sequence == Sequence.YOUTUBE:
                wav_file = audio.get_wav_from_youtube(youtube_url)
                audio.play(wav_file, led.update)
                # create new audio / start sequence
            elif new_sequence == Sequence.CANDYCANES:
                PROCESS = subprocess.Popen([sys.executable, './lib/sequences/candycanes.py'])
                pass
            elif new_sequence == Sequence.STARRYNIGHT:
                pass
            elif new_sequence == Sequence.XMAS:
                pass

    counter += 1
    time.sleep(0.001)