"""Download TikTok videos at the highest quality.

Usage: python main.py links.txt [output_folder]
       python main.py "https://vt.tiktok.com/abc/,https://vt.tiktok.com/def/"
"""

import json
import shutil
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import yt_dlp

# Item API resolver (same trick ssstik.io uses: their server signs the TikTok API
# call, we just fetch the resulting no-watermark video / slide images).
API = "https://www.tikwm.com/api/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36"


def read_links(arg):
    path = Path(arg)
    text = path.read_text(encoding="utf-8-sig") if path.is_file() else arg
    return [u.strip() for u in text.replace(",", "\n").splitlines() if u.strip()]


class Quiet:
    """Swallow yt-dlp's stderr noise; we report per link ourselves."""

    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass


def has_video(info):
    return any(f.get("url") and f.get("vcodec") not in (None, "none") for f in info.get("formats") or [])


def fetch(url, dest):
    if url.startswith("/"):
        url = "https://www.tikwm.com" + url
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://www.tiktok.com/"})
    with urllib.request.urlopen(req, timeout=180) as r, open(dest, "wb") as f:
        shutil.copyfileobj(r, f, 1 << 16)
    return f"{dest.name} ({dest.stat().st_size / 1e6:.1f} MB)"


def save_via_api(link, out):
    q = urllib.parse.urlencode({"url": link, "hd": 1})
    req = urllib.request.Request(API + "?" + q, headers={"User-Agent": UA})
    item = json.load(urllib.request.urlopen(req, timeout=60))
    if item.get("code") != 0:
        raise RuntimeError(item.get("msg") or "resolver error")
    d = item["data"]
    name = f"{d['author']['unique_id']} - {d['id']}"

    if d.get("images"):  # photo post: every slide
        return ", ".join(fetch(img, out / f"{name} {i}.jpg") for i, img in enumerate(d["images"], 1))
    src = d.get("hdplay") or d.get("play")  # hdplay = highest bitrate, no watermark
    if not src:
        raise RuntimeError("item has no video or images")
    return fetch(src, out / f"{name}.mp4")


def main():
    if len(sys.argv) not in (2, 3):
        sys.exit('usage: python main.py links.txt [output_folder]\n'
                 '       python main.py "link1,link2,..." [output_folder]')

    links = read_links(sys.argv[1])
    if not links:
        sys.exit(f"no links found in {sys.argv[1]}")

    out = Path(sys.argv[2]) if len(sys.argv) == 3 else Path.cwd()
    out.mkdir(parents=True, exist_ok=True)

    opts = {
        "format": "bv*+ba/b" if shutil.which("ffmpeg") else "b",
        "merge_output_format": "mp4",
        "outtmpl": str(out / "%(uploader,uploader_id|unknown)s - %(id)s.%(ext)s"),
        "windowsfilenames": True,
        "noplaylist": True,
        "retries": 3,
        "quiet": True,
        "noprogress": True,
        "logger": Quiet(),
        "no_warnings": True,
    }

    failures = 0
    with yt_dlp.YoutubeDL(opts) as ydl:
        for link in links:
            info = None
            try:
                info = ydl.extract_info(link, download=False)
                if has_video(info):
                    ydl.process_ie_result(info, download=True)
                    print(f"ok    {link}")
                    continue
            except Exception as e:
                reason = str(e).splitlines()[0].split(" Use --")[0].removeprefix("ERROR: ")[:140]
                print(f"note  {link}: yt-dlp: {reason}", file=sys.stderr)

            # Ad / photo posts only expose the music track to yt-dlp, so ask the
            # item API (what ssstik does server-side) for the real video or slides.
            if "tiktok" in link:
                try:
                    time.sleep(1)  # that API allows ~1 request per second
                    print(f"ok    {link} -> {save_via_api(link, out)}")
                    continue
                except Exception as e:
                    print(f"note  {link}: api: {e}", file=sys.stderr)

            try:
                if not info:
                    raise RuntimeError("no extractor result")
                ydl.process_ie_result(info, download=True)  # genuinely audio-only post
                print(f"ok    {link} (audio only)")
            except Exception as e:
                failures += 1
                print(f"FAIL  {link}: {e}", file=sys.stderr)

    print(f"\ndone: {len(links) - failures}/{len(links)} downloaded into {out}")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
