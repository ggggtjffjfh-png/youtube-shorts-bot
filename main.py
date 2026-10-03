import os
import re
import json
import random
import subprocess
from pathlib import Path

import requests
import edge_tts
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

ROOT = Path(__file__).parent
VIDEO = ROOT / "short.mp4"
AUDIO = ROOT / "voice.mp3"
TOKEN = ROOT / "token.json"

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def get_fact():
    url = "https://ru.wikipedia.org/api/rest_v1/page/random/summary"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    data = r.json()
    title = data.get("title", "Интересный факт")
    extract = data.get("extract", "")
    extract = re.sub(r"\s+", " ", extract).strip()
    extract = extract[:420]
    return title, extract

async def make_voice(text):
    communicate = edge_tts.Communicate(text, "ru-RU-DmitryNeural")
    await communicate.save(str(AUDIO))

def make_video(title, text):
    safe = (title + ". " + text).replace("\\", "\\\\").replace("'", "\\'")
    # FFmpeg creates a vertical 30-second Short with animated background and captions.
    vf = (
        "scale=1080:1920,format=yuv420p,"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"text='{safe}':fontcolor=white:fontsize=58:line_spacing=18:"
        "x=(w-text_w)/2:y=(h-text_h)/2:"
        "box=1:boxcolor=black@0.55:boxborderw=35"
    )
    cmd = [
        "ffmpeg","-y",
        "-f","lavfi","-i","color=c=0x171717:s=1080x1920:r=30",
        "-i",str(AUDIO),
        "-vf",vf,
        "-t","30",
        "-c:v","libx264","-preset","veryfast","-crf","27",
        "-c:a","aac","-b:a","128k",
        "-shortest",str(VIDEO)
    ]
    subprocess.run(cmd, check=True)

def upload(title, description):
    if not TOKEN.exists():
        raise RuntimeError("token.json is missing. Create a YouTube OAuth token once and add it as a GitHub secret named YOUTUBE_TOKEN_JSON.")

    creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": ["shorts", "факты", "интересное", "знания"],
            "categoryId": "27"
        },
        "status": {
            "privacyStatus": "public",
            "selfDeclaredMadeForKids": False
        }
    }
    media = MediaFileUpload(str(VIDEO), mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = request.execute()
    print("Uploaded:", response.get("id"))

def main():
    title, fact = get_fact()
    script = f"Знаешь ли ты? {title}. {fact}"
    import asyncio
    asyncio.run(make_voice(script))
    make_video(title, fact)
    upload(f"Ты точно этого не знал 😳 {title} #shorts", script + "\n\nИсточник: русская Википедия.")
    print("DONE")

if __name__ == "__main__":
    main()
