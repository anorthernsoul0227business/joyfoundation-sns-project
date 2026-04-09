#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""X投稿スクリプト"""

import os, sys, json, requests
from requests_oauthlib import OAuth1
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

auth = OAuth1(
    os.getenv('X_CONSUMER_KEY'),
    os.getenv('X_CONSUMER_SECRET'),
    os.getenv('X_ACCESS_TOKEN'),
    os.getenv('X_ACCESS_TOKEN_SECRET')
)

def post_tweet(text):
    # Try v1.1 first
    resp = requests.post(
        'https://api.twitter.com/1.1/statuses/update.json',
        auth=auth,
        data={'status': text}
    )
    if resp.status_code == 200:
        data = resp.json()
        tweet_id = str(data['id'])
        print(f"Posted (v1.1)! Tweet ID: {tweet_id}")
        print(f"URL: https://x.com/SFH_Science/status/{tweet_id}")
        return tweet_id

    # Try v2
    resp2 = requests.post(
        'https://api.twitter.com/2/tweets',
        auth=auth,
        json={'text': text}
    )
    if resp2.status_code in (200, 201):
        data = resp2.json()
        tweet_id = data['data']['id']
        print(f"Posted (v2)! Tweet ID: {tweet_id}")
        print(f"URL: https://x.com/SFH_Science/status/{tweet_id}")
        return tweet_id

    print(f"v1.1 Error {resp.status_code}: {resp.text}")
    print(f"v2 Error {resp2.status_code}: {resp2.text}")
    return None

def pin_tweet(tweet_id):
    resp = requests.post(
        'https://api.twitter.com/1.1/account/pin_tweet.json',
        auth=auth,
        data={'id': tweet_id}
    )
    if resp.status_code == 200:
        print("Pinned!")
    else:
        print(f"Pin result: {resp.status_code} {resp.text}")

if __name__ == '__main__':
    text = sys.argv[1] if len(sys.argv) > 1 else None
    if text:
        tweet_id = post_tweet(text)
        if tweet_id and '--pin' in sys.argv:
            pin_tweet(tweet_id)
    else:
        print("Usage: python3 post_x.py 'tweet text' [--pin]")
