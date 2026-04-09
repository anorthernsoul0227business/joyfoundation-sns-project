#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Xプロフィール更新"""

import os, requests
from requests_oauthlib import OAuth1
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

auth = OAuth1(
    os.getenv('X_CONSUMER_KEY'),
    os.getenv('X_CONSUMER_SECRET'),
    os.getenv('X_ACCESS_TOKEN'),
    os.getenv('X_ACCESS_TOKEN_SECRET')
)

new_bio = """サウンドヒーリング協会 公式
心と体に自然のリズムを取り戻す「Harmonic Revolution」
✨ 自然音・体感音響・呼吸と声の３つのメソッド
📍 自由が丘 Harmonic Science
2001年設立｜25年の実績"""

new_name = "サウンドヒーリング協会"

resp = requests.post(
    'https://api.twitter.com/1.1/account/update_profile.json',
    auth=auth,
    data={
        'description': new_bio,
        'name': new_name
    }
)

if resp.status_code == 200:
    data = resp.json()
    print(f"Updated! Name: {data['name']}")
    print(f"Bio: {data['description']}")
else:
    print(f"Error {resp.status_code}: {resp.text}")
