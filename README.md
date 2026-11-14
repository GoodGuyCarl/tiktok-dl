# tiktok-dl

Batch download TikTok videos and photo posts at the highest available quality, without a watermark.

One script, `main.py`. No config, no accounts, no browser cookies.

## Requirements

- Python 3.10+
- `yt-dlp` — `pip install yt-dlp`
- Optional: `ffmpeg` on `PATH` for best video + audio merging. Without it the script downloads the best single-file format instead.

## Usage

```bash
# links from a file (one per line, or comma separated)
python main.py links.txt

# links straight on the command line
python main.py "https://vt.tiktok.com/ZSpmMXvej/,https://vt.tiktok.com/ZSpmrYdJs/"

# choose the output folder
python main.py links.txt output_folder
```

The first argument is a file path if that file exists, otherwise it is treated as the link list itself. The output folder defaults to the current directory and is created if missing. `links.txt` can start with a UTF-8 BOM; it is stripped.

## Output

Files are named `<uploader> - <video_id>.<ext>`, e.g. `thehappy_cart - 7661098917920017685.mp4`.

Photo posts save one JPEG per slide: `<uploader> - <post_id> 1.jpg`, `... 2.jpg`, and so on.

## How it works

For each link:

1. **yt-dlp** extracts the post and downloads it if it has a real video stream.
2. If yt-dlp only finds a music track (photo posts, some ads), the **tikwm.com API** is asked for the no-watermark video (`hdplay`) or the slide images. This path waits 1 second between requests because the API rate-limits.
3. If the post genuinely has no video, the audio track is saved instead.

Every link prints one status line:

```
ok    https://vt.tiktok.com/ZSpmMXvej/
note  https://vt.tiktok.com/ZSpmrYdJs/: yt-dlp: <reason>    (fallback attempted)
FAIL  https://vt.tiktok.com/ZSpmh771q/: <reason>
```

Progress ends with `done: N/M downloaded into <folder>`.

## Exit codes

- `0` — every link downloaded
- `1` — at least one link failed (the rest still downloaded)
- usage error — wrong number of arguments, or no links found

## Limitations

- The tikwm.com fallback is a third-party service: it can rate-limit, change, or go down, and it will fail on private, deleted, or region-locked posts.
- If a post fails both yt-dlp and the API, it is reported as `FAIL` and skipped; rerunning the same command retries everything, so keep the failed links in a separate list.
- No resume or download-history tracking. Existing files are skipped by yt-dlp only if it recognizes them as already downloaded.
- Video quality depends on what the post exposes publicly.
