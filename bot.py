import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.filters import Command
bot = Bot(token="ТОКЕН_БОТА")  # ← замени на свой токен
dp = Dispatcher()
@dp.message(Command("start"))
async def start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🌌 Запустить Cosmic Treasure Hunt", web_app=WebAppInfo(url="https://твой-vercel.app"))]])
    await message.answer("Cosmic Treasure Hunt запущен!", reply_markup=kb)
asyncio.run(dp.start_polling(bot))