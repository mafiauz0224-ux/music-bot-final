from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from database import create_user_if_not_exists
from locales import t

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    await create_user_if_not_exists(message.from_user.id, message.from_user.username)
    await message.answer(t("welcome", "uz"))
