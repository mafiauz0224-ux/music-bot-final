from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from database import create_user_if_not_exists

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await create_user_if_not_exists(message.from_user.id, message.from_user.username)
    await message.answer(
        "Assalomu alaykum! Musiqa botga xush kelibsiz!\n\n"
        "Qoshiq nomini yozing - top 10 variantni korsataman\n"
        "TikTok/Instagram/YouTube havolasini yuboring - videoni yuklab beraman\n\n"
        "Buyruqlar:\n"
        "/top - eng kop soralgan qoshiqlar\n"
        "/playlists - pleylistlaringiz"
    )