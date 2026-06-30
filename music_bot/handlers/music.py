import asyncio
import hashlib
import os
import uuid

from aiogram import F, Router
from aiogram.types import CallbackQuery, FSInputFile, Message

import keyboards as kb
from config import DOWNLOAD_DIR
from database import (
    cache_song,
    get_cached_song,
    get_user_language,
    log_song_request,
)
from locales import t
from utils.downloader import download_audio, search_youtube_list

router = Router()

# search_id -> qidiruv natijalari ro'yxati (vaqtinchalik, RAM'da).
# Bu kichik matnli ma'lumot (sarlavha/davomiylik/havola), shu sabab
# disk muammosi keltirib chiqarmaydi - lekin baribir vaqt o'tib o'zi
# o'chib ketishi uchun TTL beramiz.
SEARCH_RESULTS_CACHE: dict[str, list[dict]] = {}
SEARCH_CACHE_TTL = 10 * 60  # 10 daqiqa

_background_tasks: set[asyncio.Task] = set()


def _run_in_background(coro):
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


async def _expire_search(search_id: str):
    await asyncio.sleep(SEARCH_CACHE_TTL)
    SEARCH_RESULTS_CACHE.pop(search_id, None)


def _format_duration(seconds) -> str:
    seconds = int(seconds or 0)
    m, s = divmod(seconds, 60)
    return f"{m}:{s:02d}"


async def search_and_show_results(message: Message, query: str):
    """Qo'shiq nomi bo'yicha TOP 10 nomzodni ro'yxat qilib, raqamli
    tugmalar bilan ko'rsatadi. Hech narsa avtomatik yuklanmaydi -
    foydalanuvchi qaysi raqamni bossa, faqat o'sha bitta qo'shiq yuklanadi."""
    lang = await get_user_language(message.from_user.id)
    status_msg = await message.answer(t("searching", lang, query=query))

    try:
        results = await search_youtube_list(query, limit=10)
    except Exception:
        results = []

    if not results:
        await status_msg.edit_text(t("not_found", lang))
        return

    search_id = uuid.uuid4().hex[:10]
    SEARCH_RESULTS_CACHE[search_id] = results
    _run_in_background(_expire_search(search_id))

    lines = [
        f"{i + 1}. {r['title']} — {_format_duration(r.get('duration'))}"
        for i, r in enumerate(results)
    ]
    text = t("search_results_title", lang, query=query) + "\n\n" + "\n".join(lines)
    await status_msg.edit_text(text, reply_markup=kb.search_results_keyboard(search_id, len(results)))


# Eski nom bilan ham ishlatilishi mumkin - search.py va recognize.py shu nomdan foydalanadi
handle_music_search = search_and_show_results


@router.callback_query(F.data.startswith("pick_"))
async def pick_song_callback(call: CallbackQuery):
    lang = await get_user_language(call.from_user.id)
    _, search_id, idx_str = call.data.split("_", 2)
    idx = int(idx_str)

    results = SEARCH_RESULTS_CACHE.get(search_id)
    if not results or idx >= len(results):
        await call.answer(t("song_not_found", lang), show_alert=True)
        return

    chosen = results[idx]
    await call.answer(t("downloading_chosen", lang))

    query_hash = hashlib.md5(chosen["url"].encode()).hexdigest()
    cached = await get_cached_song(query_hash)

    if cached:
        await call.message.answer_audio(
            cached["file_id"],
            caption=t("here_is_song", lang, title=cached["title"]),
            reply_markup=kb.song_action_keyboard(query_hash),
        )
        await log_song_request(call.from_user.id, chosen["title"], cached["title"])
        return

    try:
        filepath, title = await download_audio(chosen["url"], DOWNLOAD_DIR, use_search=False)
    except Exception:
        await call.message.answer(t("not_found", lang))
        return

    audio = FSInputFile(filepath)
    sent = await call.message.answer_audio(
        audio,
        title=title,
        caption=t("here_is_song", lang, title=title),
        reply_markup=kb.song_action_keyboard(query_hash),
    )
    await cache_song(query_hash, title, sent.audio.file_id, "youtube")
    await log_song_request(call.from_user.id, title, title)

    try:
        os.remove(filepath)
    except OSError:
        pass


@router.callback_query(F.data.startswith("redownload_"))
async def redownload_callback(call: CallbackQuery):
    lang = await get_user_language(call.from_user.id)
    query_hash = call.data.replace("redownload_", "")
    cached = await get_cached_song(query_hash)
    if not cached:
        await call.answer(t("song_not_found", lang), show_alert=True)
        return
    await call.message.answer_audio(
        cached["file_id"],
        caption=t("here_is_song", lang, title=cached["title"]),
        reply_markup=kb.song_action_keyboard(query_hash),
    )
    await call.answer()
