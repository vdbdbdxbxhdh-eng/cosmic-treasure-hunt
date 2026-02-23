import asyncio, logging, json, os, random
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, LabeledPrice, PreCheckoutQuery, SuccessfulPayment
from aiogram.filters import Command
import aiosqlite

load_dotenv()
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

DB = "bot.db"

async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.executescript('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                stars INTEGER DEFAULT 500,
                tickets INTEGER DEFAULT 50
            );
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                name TEXT,
                rarity TEXT,
                emoji TEXT,
                value INTEGER,
                gift_id TEXT
            );
        ''')
        await db.commit()

prizes = [
    {"name":"Обычный Астероид","rarity":"Common","emoji":"☄️","value":10},
    {"name":"Комета Оорта","rarity":"Rare","emoji":"🌠","value":50},
    {"name":"Туманность Ориона","rarity":"Epic","emoji":"🌌","value":250},
    {"name":"Чёрная Дыра Sgr A*","rarity":"Legendary","emoji":"⚫","value":1200},
    {"name":"Корабль Древних","rarity":"Mythic","emoji":"🛸","value":5000}
]

@dp.pre_checkout_query()
async def pre_checkout(pre: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    if message.successful_payment.currency == "XTR":
        amount = message.successful_payment.total_amount
        async with aiosqlite.connect(DB) as db:
            await db.execute("UPDATE users SET stars = stars + ? WHERE id = ?", (amount, message.from_user.id))
            await db.commit()
        await message.answer(f"✅ +{amount} Stars зачислено на баланс!")

@dp.message(Command("start"))
async def start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🌌 Запустить Cosmic Treasure Hunt", web_app=WebAppInfo(url=os.getenv("WEBAPP_URL")))]])
    await message.answer("Добро пожаловать в Cosmic Treasure Hunt!", reply_markup=kb)

@dp.message(F.web_app_data)
async def webapp_data(message: Message):
    data = json.loads(message.web_app_data.data)
    user_id = message.from_user.id
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))
        if data.get("action") == "buy_stars":
            amount = data.get("amount", 100)
            await bot.send_invoice(
                chat_id=message.chat.id,
                title="Пополнение Stars",
                description=f"Купить {amount} Stars",
                payload=f"topup_{user_id}",
                provider_token="",
                currency="XTR",
                prices=[LabeledPrice(label=f"{amount} Stars", amount=amount)]
            )
        elif data.get("action") == "open_case":
            cost = data.get("cost", 0)
            async with db.execute("SELECT stars FROM users WHERE id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                stars = row[0] if row else 500
            if cost > 0 and stars < cost:
                return await message.answer(json.dumps({"success": False, "error": "Недостаточно Stars"}))
            if cost > 0:
                await db.execute("UPDATE users SET stars = stars - ? WHERE id = ?", (cost, user_id))
            prize = random.choice(prizes)
            await db.execute("INSERT INTO inventory (user_id, name, rarity, emoji, value) VALUES (?,?,?,?,?)",
                            (user_id, prize["name"], prize["rarity"], prize["emoji"], prize["value"]))
            await db.commit()
            await message.answer(json.dumps({"success": True, "prize": prize}))

async def main():
    await init_db()
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())