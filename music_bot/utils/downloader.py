import asyncio
import os

import yt_dlp

from config import MAX_VIDEO_HEIGHT


def _run_audio_download(opts: dict, url_or_query: str):
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url_or_query, download=True)
        if "entries" in info:
            info = info["entries"][0]
        filename = ydl.prepare_filename(info)
        base, _ = os.path.splitext(filename)
        mp3_path = base + ".mp3"
        return mp3_path, info.get("title", url_or_query)


async def download_audio(
    url_or_query: str, out_dir: str, quality: str = "192", use_search: bool = True
) -> tuple[str, str]:
    """Audio yuklab oladi.

    use_search=True bo'lsa, `url_or_query` matn sifatida qaraladi va eng mos
    1 ta natija yuklanadi (eski xulq-atvor).
    use_search=False bo'lsa, `url_or_query` to'g'ridan-to'g'ri video havolasi
    deb qaraladi (qidiruv ro'yxatidan tanlangan aniq qo'shiq uchun)."""
    os.makedirs(out_dir, exist_ok=True)
    outtmpl = os.path.join(out_dir, "%(id)s.%(ext)s")
    opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": quality,
            }
        ],
    }
    if use_search:
        opts["default_search"] = "ytsearch1"
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run_audio_download, opts, url_or_query)


def _run_search_list(opts: dict, query: str):
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(query, download=False)
        entries = info.get("entries", [info]) if info else []
        results = []
        for e in entries:
            if not e:
                continue
            results.append(
                {
                    "title": e.get("title", "Noma'lum"),
                    "duration": e.get("duration") or 0,
                    "url": e.get("webpage_url") or f"https://www.youtube.com/watch?v={e.get('id')}",
                }
            )
        return results


async def search_youtube_list(query: str, limit: int = 10) -> list[dict]:
    """Qo'shiq nomi bo'yicha YouTube'dan TOP N ta nomzodni (nomi, davomiyligi,
    havolasi) qaytaradi - hech narsa yuklanmaydi, foydalanuvchi keyin
    o'zi birini tanlaydi."""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "default_search": f"ytsearch{limit}",
        "extract_flat": False,
    }
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run_search_list, opts, query)


def _run_video_download(opts: dict, url: str):
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        base, _ = os.path.splitext(filename)
        mp4_path = base + ".mp4"
        if not os.path.exists(mp4_path):
            mp4_path = filename
        return mp4_path, info.get("title", "video")


async def download_video(url: str, out_dir: str, max_height: int = MAX_VIDEO_HEIGHT) -> tuple[str, str]:
    """TikTok / Instagram / YouTube / Pinterest va boshqa yt-dlp qo'llab-quvvatlaydigan
    manbalardan videoni yuklab oladi (default: 720p gacha)."""
    os.makedirs(out_dir, exist_ok=True)
    outtmpl = os.path.join(out_dir, "%(id)s.%(ext)s")
    opts = {
        "format": f"bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]/best",
        "outtmpl": outtmpl,
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run_video_download, opts, url)


async def extract_audio_from_file(video_path: str, out_dir: str) -> str:
    """Mahalliy diskdagi video fayldan ffmpeg yordamida audio ajratib oladi."""
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(video_path))[0]
    audio_path = os.path.join(out_dir, f"{base}_audio.mp3")

    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "libmp3lame", "-q:a", "2",
        audio_path,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
    )
    await proc.wait()

    if proc.returncode != 0 or not os.path.exists(audio_path):
        raise RuntimeError("ffmpeg orqali audio ajratib bo'lmadi")

    return audio_path
