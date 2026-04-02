#!/usr/bin/env python3
"""Validate Google Drive -> lh3 URL compatibility for Instagram Graph API image_url."""

from __future__ import annotations

import argparse
import re
import sys
from typing import Optional

import requests


def extract_drive_file_id(url: str) -> Optional[str]:
    patterns = [
        r"/file/d/([a-zA-Z0-9_-]+)",
        r"[?&]id=([a-zA-Z0-9_-]+)",
        r"/d/([a-zA-Z0-9_-]+)",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


def build_lh3_url(file_id: str) -> str:
    return f"https://lh3.googleusercontent.com/d/{file_id}"


def probe_image(url: str, timeout_sec: int = 20) -> tuple[bool, int, str]:
    r = requests.get(url, timeout=timeout_sec, allow_redirects=True)
    content_type = r.headers.get("Content-Type", "")
    ok = 200 <= r.status_code < 300 and content_type.startswith("image/")
    return ok, r.status_code, content_type


def create_ig_container(ig_user_id: str, access_token: str, image_url: str, caption: str) -> tuple[bool, str]:
    endpoint = f"https://graph.facebook.com/v23.0/{ig_user_id}/media"
    payload = {
        "image_url": image_url,
        "caption": caption,
        "access_token": access_token,
    }
    resp = requests.post(endpoint, data=payload, timeout=30)
    if resp.status_code in (200, 201):
        creation_id = resp.json().get("id", "")
        return True, creation_id
    return False, f"{resp.status_code} {resp.text}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify lh3 URL for IG Graph API image_url")
    parser.add_argument("--drive-url", required=True, help="Google Drive file URL")
    parser.add_argument("--check-ig-api", action="store_true", help="Try /media container creation")
    parser.add_argument("--ig-user-id", default="")
    parser.add_argument("--ig-access-token", default="")
    parser.add_argument("--caption", default="lh3 validation test post")
    args = parser.parse_args()

    file_id = extract_drive_file_id(args.drive_url)
    if not file_id:
        print("[NG] Failed to extract file_id from drive URL")
        return 2

    lh3_url = build_lh3_url(file_id)
    print(f"[INFO] file_id: {file_id}")
    print(f"[INFO] lh3_url: {lh3_url}")

    ok, status, ctype = probe_image(lh3_url)
    print(f"[INFO] GET status={status}, content_type={ctype}")
    if not ok:
        print("[NG] lh3 URL does not satisfy image fetch requirement")
        return 3

    print("[OK] lh3 URL is publicly retrievable as image/*")

    if args.check_ig_api:
        if not args.ig_user_id or not args.ig_access_token:
            print("[NG] --check-ig-api requires --ig-user-id and --ig-access-token")
            return 4

        ig_ok, detail = create_ig_container(
            ig_user_id=args.ig_user_id,
            access_token=args.ig_access_token,
            image_url=lh3_url,
            caption=args.caption,
        )
        if ig_ok:
            print(f"[OK] IG media container created: creation_id={detail}")
            return 0

        print(f"[NG] IG media container failed: {detail}")
        return 5

    return 0


if __name__ == "__main__":
    sys.exit(main())
