from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def song_action_keyboard(song_hash: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🔁 Yana yukla", callback_data=f"redownload_{song_hash}"),
                InlineKeyboardButton(text="➕ Pleylistga qo'sh", callback_data=f"addplaylist_{song_hash}"),
            ],
        ]
    )


def video_action_keyboard(video_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎙 Ovozni ajratish", callback_data=f"extract_audio_{video_id}")],
            [InlineKeyboardButton(text="🎵 Musiqasini topish", callback_data=f"findmusic_{video_id}")],
        ]
    )


def search_results_keyboard(search_id: str, count: int) -> InlineKeyboardMarkup:
    """Qidiruv natijalari uchun 1...N raqamli tugmalar (har qatorda 5 tadan)."""
    buttons: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for i in range(count):
        row.append(InlineKeyboardButton(text=str(i + 1), callback_data=f"pick_{search_id}_{i}"))
        if len(row) == 5:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def quality_keyboard(song_hash: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="128 kbps", callback_data=f"q_128_{song_hash}"),
                InlineKeyboardButton(text="320 kbps", callback_data=f"q_320_{song_hash}"),
            ]
        ]
    )
