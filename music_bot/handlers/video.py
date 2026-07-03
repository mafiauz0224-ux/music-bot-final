import asyncio
import os
import time

from aiogram import F, Router
from aiogram.types import CallbackQuery, FSInputFile, Message

import keyboards as kb
from config import DOWNLOAD_DIR
from database import get_user_language
from locales import t
from utils.downloader import download_video, extract_audio_from_file

router = Router()

VIDEO_FILE_CACHE: dict[str, dict] = {}
CLEANUP_DELAY_SECONDS = 15 * 60

_background_tasks: set[asyncio.Task] = set()


def _run_in_background(coro):
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


async def _schedule_cleanup(video_id: str, filepath: str):
    await asyncio.sleep(CLEANUP_DELAY_SECONDS)
    VIDEO_FILE_CACHE.pop(video_id, None)
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except OSError:
        pass


async def handle_video_link(message: Message, url: str):
    lang = await get_user_language(message.from_user.id)
    status_msg = await message.answer("⬇️ Video yuklanmoqda, biroz kuting (1-3 daqiqa)...")

    try:
        filepath, title = await download_video(url, DOWNLOAD_DIR)
    except Exception as e:
        err = str(e).lower()
        if "sign in" in err or "login" in err or "cookie" in err:
            await status_msg.edit_text(
                "❌ Bu video yuklab bo'lmadi.\n\n"
                "Instagram va YouTube ba'zi videolar uchun login talab qiladi.\n"
                "TikTok havolalarini sinab ko'ring — ular yaxshiroq ishlaydi."
            )
        else:
            await status_msg.edit_text(
                "❌ Videoni yuklab bo'lmadi.\n"
                "Havola noto'g'ri yoki manba qo'llab-quvvatlanmaydi."
            )
        return

    video_id = str(int(time.time() * 1000))
    VIDEO_FILE_CACHE[video_id] = {"path": filepath, "title": title}

    try:
        video_file = FSInputFile(filepath)
        await message.answer_video(
            video_file,
            caption=f"🎬 {title}",
            reply_markup=kb.video_action_keyboard(video_id),
        )
    except Exception:
        await status_msg.edit_text("❌ Video juda katta (50MB dan oshiq), yuborib bo'lmadi.")
        return

    await status_msg.delete()
    _run_in_background(_schedule_cleanup(video_id, filepath))


@router.callback_query(F.data.startswith("extract_audio_"))
async def extract_audio_callback(call: CallbackQuery):
    lang = await get_user_language(call.from_user.id)
    video_id = call.data.replace("extract_audio_", "")
    info = VIDEO_FILE_CACHE.get(video_id)

    if not info or not os.path.exists(info["path"]):
        await call.answer("Fayl eskirgan, havolani qaytadan yuboring", show_alert=True)
        return

    await call.answer("🎧 Ovoz ajratilmoqda...")
    try:
        audio_path = await extract_audio_from_file(info["path"], DOWNLOAD_DIR)
        await call.message.answer_audio(FSInputFile(audio_path))
        os.remove(audio_path)
    except Exception:
        await call.message.answer("❌ Ovozni ajratishda xatolik.")


@router.callback_query(F.data.startswith("findmusic_"))
async def find_music_callback(call: CallbackQuery):
    lang = await get_user_language(call.from_user.id)
    video_id = call.data.replace("findmusic_", "")
    info = VIDEO_FILE_CACHE.get(video_id)

    if not info:
        await call.answer("Fayl eskirgan", show_alert=True)
        return

    await call.answer()
    from handlers.music import search_and_show_results
    await search_and_show_results(call.message, info["title"])