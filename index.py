import atexit
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
POLL_TWITTER = False
POLL_SEC = 5

def persist_last_tweet_id(tweet_id):
    with open('./last_tweet.txt', 'w') as f:
        f.write(tweet_id)

def get_last_tweet_id():
    try:
        with open('./last_tweet.txt') as f:
            return f.read()
    except:
        return None

def run_sequence(file):
    print(f"Running sequence at {file}")
    return subprocess.Popen([sys.executable, file])

def main():
    print(sys.argv)
    if len(sys.argv) > 1:
        manual_sequence = sys.argv[1]
        if 'youtube' in manual_sequence:
            wav_file = audio.get_wav_from_youtube(manual_sequence)
            audio.play(wav_file, led.update)
        else:
            PROCESS = run_sequence(manual_sequence)
            SEQUENCE = 'manual'

    LAST_TWEET_ID = get_last_tweet_id()
    counter = 0
    while True:
        if counter % POLL_SEC == 0:
            print(f"Checking for new tweets, last id is {LAST_TWEET_ID}")
            if POLL_TWITTER:
                (
                    new_sequence,
                    youtube_url,
                    last_tweet_id
                ) = twt.poll_for_tweets(LAST_TWEET_ID)
            else:
                new_sequence = False
                youtube_url = None
                last_tweet_id = LAST_TWEET_ID

            LAST_TWEET_ID = last_tweet_id
            persist_last_tweet_id(LAST_TWEET_ID)
            print(f"Got tweets, id is {LAST_TWEET_ID}")

            try:
                if new_sequence:
                    SEQUENCE = new_sequence
                    print(f"Discovered new sequence {new_sequence}, {youtube_url}")

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
                        PROCESS = run_sequence('./lib/sequences/candycanes.py')
                    elif new_sequence == Sequence.STARRYNIGHT:
                        PROCESS = run_sequence('./lib/sequences/starrynight.py')
                    elif new_sequence == Sequence.XMAS:
                        PROCESS = run_sequence('./lib/sequences/xmas.py')
                    elif new_sequence == Sequence.OFF:
                        PROCESS = run_sequence('./lib/sequences/off.py')
                    else:
                        print(f"Could not play sequence {new_sequence}")
                else:
                    # Default sequence to play if none
                    if not SEQUENCE:
                        SEQUENCE = Sequence.CANDYCANES
                        PROCESS = run_sequence('./lib/sequences/candycanes.py')

            except Exception as e:
                print(e)
                print(f"Failed at tweet {LAST_TWEET_ID}")

        counter += 1
        time.sleep(1)

def cleanup():
    if PROCESS:
        PROCESS.terminate()

atexit.register(cleanup)

if __name__ == "__main__":
    main()