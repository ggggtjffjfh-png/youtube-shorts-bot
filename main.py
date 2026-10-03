import re
import subprocess
from pathlib import Path
from datetime import datetime, timezone

import requests
import edge_tts

ROOT = Path(__file__).parent
OUTPUT = ROOT / "output"
OUTPUT.mkdir(exist_ok=True)
AUDIO = OUTPUT / "voice.mp3"

def get_fact():
    url = "https://ru.wikipedia.org/api/rest_v1/page/random/summary"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    data = r.json()
    title = data.get("title", "Интересный факт")
    extract = re.sub(r"\s+", " ", data.get("extract", "")).strip()
    return title, extract[:420]

async def make_voice(text):
    communicate = edge_tts.Communicate(text, "ru-RU-DmitryNeural")
    await communicate.save(str(AUDIO))

def make_video(title, text):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    video = OUTPUT / f"short_{stamp}.mp4"
    safe = (title + ". " + text).replace("\\", "\\\\").replace("'", "\\'")
    vf = (
        "format=yuv420p,"
        "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"text='{safe}':fontcolor=white:fontsize=58:line_spacing=18:"
        "x=(w-text_w)/2:y=(h-text_h)/2:"
        "box=1:boxcolor=black@0.55:boxborderw=35"
    )
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=0x171717:s=1080x1920:r=30",
        "-i", str(AUDIO),
        "-vf", vf,
        "-t", "30",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "27",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest", str(video)
    ]
    subprocess.run(cmd, check=True)
    return video

def main():
    title, fact = get_fact()
    script = f"Знаешь ли ты? {title}. {fact}"
    import asyncio
    asyncio.run(make_voice(script))
    video = make_video(title, fact)
    print(f"VIDEO_READY={video}")
    print(f"TITLE=Ты точно этого не знал 😳 {title} #shorts")
    print("DONE")

if __name__ == "__main__":
    main()
