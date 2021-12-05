import os
import re
import requests
import tldextract
import validators
from constants import Sequence

user_handle = '@RockridgeLights'
user_id = '1467030371694886912'

def auth():
    return os.getenv('TOKEN')

def create_headers(bearer_token):
    headers = {'Authorization': 'Bearer {}'.format(bearer_token)}
    return headers

def get_mentions(headers, since_id):
    get_mentions_endpoint = 'https://api.twitter.com/2/users/{}/mentions'.format(user_id)
    query_params = {}
    if since_id:
        query_params = {'since_id': since_id}

    response = requests.request('GET', get_mentions_endpoint, headers = headers, params = query_params)

    if response.status_code != 200:
        # oops
        return ''

    mentions = response.json()
    if mentions['meta']['result_count'] == 0:
        # nothing to see here
        return ''
    return mentions['meta']['newest_id']

def get_tweet(headers, tweet_id):
    get_tweet_endpoint = 'https://api.twitter.com/2/tweets/{}'.format(tweet_id)
    response = requests.request('GET', get_tweet_endpoint, headers = headers)

    if response.status_code != 200:
        #oops
        return

    tweet = response.json()
    return tweet['data']['text']

def parse_tweet(text):
    parsed_text = text.split("{} play ".format(user_handle), 1)
    if len(parsed_text) == 2:
        item = parsed_text[1]
        if validators.url(item):
            url = requests.get(item).url
            domain = tldextract.extract(url).domain
            if domain == 'youtube':
                return (Sequence.YOUTUBE, url)
        elif item == 'candycanes':
            return (Sequence.CANDYCANES, None)
        elif item == 'starrynight':
            return (Sequence.STARRYNIGHT, None)
        elif item == 'xmas':
            return (Sequence.XMAS, None)
        else:
            # rip bad tweet
            return

def poll_for_tweets(last_tweet_id):
    headers = create_headers(auth())
    tweet_id = get_mentions(headers, last_tweet_id)
    if tweet_id != '':
        # we got somethin'
        tweet = get_tweet(headers, tweet_id)
        (sequence, youtube_url) = parse_tweet(tweet)
        return (sequence, youtube_url, tweet_id)
    return 'nothing to see here'
