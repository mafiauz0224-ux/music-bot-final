import asyncio
import os

import yt_dlp

from config import MAX_VIDEO_HEIGHT


async def search_youtube_list(query: str, limit: int = 10) -> list[dict]:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "default_search": f"scsearch{limit}",
        "extract_flat": True,
    }

    def _search():
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(query, download=False)
            entries = info.get("entries", []) if info else []
            results = []
            for e in entries:
                if not e:
                    continue
                results.append({
                    "title": e.get("title", "Noma'lum"),
                    "duration": e.get("duration") or 0,
                    "url": e.get("url") or e.get("webpage_url", ""),
                })
            return results

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _search)


async def download_audio(url_or_query: str, out_dir: str, quality: str = "192", use_search: bool = True) -> tuple[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    outtmpl = os.path.join(out_dir, "%(id)s.%(ext)s")
    opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": quality,
        }],
    }
    if use_search:
        opts["default_search"] = "scsearch1"

    def _download():
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url_or_query, download=True)
            if "entries" in info:
                info = info["entries"][0]
            filename = ydl.prepare_filename(info)
            base, _ = os.path.splitext(filename)
            return base + ".mp3", info.get("title", url_or_query)

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _download)


async def download_video(url: str, out_dir: str, max_height: int = MAX_VIDEO_HEIGHT) -> tuple[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    outtmpl = os.path.join(out_dir, "%(id)s.%(ext)s")
    opts = {
        "format": f"bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]/best",
        "outtmpl": outtmpl,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "http_headers": {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        },
    }

    def _download():
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            base, _ = os.path.splitext(filename)
            mp4 = base + ".mp4"
            return (mp4 if os.path.exists(mp4) else filename), info.get("title", "video")

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _download)


async def extract_audio_from_file(video_path: str, out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(video_path))[0]
    audio_path = os.path.join(out_dir, f"{base}_audio.mp3")
    cmd = ["ffmpeg", "-y", "-i", video_path, "-vn", "-acodec", "libmp3lame", "-q:a", "2", audio_path]
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
    await proc.wait()
    if proc.returncode != 0 or not os.path.exists(audio_path):
        raise RuntimeError("ffmpeg orqali audio ajratib bolmadi")
    return audio_path