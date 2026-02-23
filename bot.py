import asyncio, logging, json, os, random
from datetime import datetime
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, LabeledPrice, PreCheckoutQuery, SuccessfulPayment
from aiogram.filters import Command
from sqlalchemy import Column, Integer, String, BigInteger, DateTime, ForeignKey, select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

load_dotenv()
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

# ====================== БАЗА ДАННЫХ ======================
engine = create_async_engine(os.getenv("DATABASE_URL"), echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase): pass

class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True)
    username = Column(String, nullable=True)
    stars = Column(Integer, default=500)
    tickets = Column(Integer, default=50)
    last_free_case = Column(DateTime, nullable=True)

class InventoryItem(Base):
    __tablename__ = "inventory"
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"))
    name = Column(String)
    rarity = Column(String)
    emoji = Column(String)
    value = Column(Integer, default=0)
    gift_id = Column(String, nullable=True)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# ====================== ПРИЗЫ ======================
prizes = [
    {"name":"Обычный Астероид","rarity":"Common","emoji":"☄️","value":10},
    {"name":"Комета Оорта","rarity":"Rare","emoji":"🌠","value":50},
    {"name":"Туманность Ориона","rarity":"Epic","emoji":"🌌","value":250},
    {"name":"Чёрная Дыра Sgr A*","rarity":"Legendary","emoji":"⚫","value":1200},
    {"name":"Корабль Древних","rarity":"Mythic","emoji":"🛸","value":5000}
]

available_gifts = {}

# ====================== TELEGRAM STARS ======================
@dp.pre_checkout_query()
async def pre_checkout(pre: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre.id, ok=True)

@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    payment = message.successful_payment
    if payment.currency == "XTR":
        amount = payment.total_amount
        user_id = message.from_user.id
        async with AsyncSessionLocal() as session:
            user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
            if user:
                user.stars += amount
                await session.commit()
        await message.answer(f"✅ +{amount} Stars зачислено!\nТеперь у тебя {user.stars} Stars", parse_mode="HTML")

# ====================== КОМАНДЫ ======================
@dp.message(Command("start"))
async def start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🌌 Запустить Cosmic Treasure Hunt", web_app=WebAppInfo(url=os.getenv("WEBAPP_URL")))]])
    await message.answer("Добро пожаловать в Cosmic Treasure Hunt!", reply_markup=kb)

@dp.message(F.web_app_data)
async def webapp_data(message: Message):
    data = json.loads(message.web_app_data.data)
    user_id = message.from_user.id
    async with AsyncSessionLocal() as session:
        user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
        if not user:
            user = User(id=user_id, username=message.from_user.username)
            session.add(user)
            await session.commit()

        action = data.get("action")
        if action == "buy_stars":
            amount = data.get("amount", 100)
            try:
                await bot.send_invoice(
                    chat_id=message.chat.id,
                    title="Пополнение Stars",
                    description=f"Купить {amount} Stars",
                    payload=f"stars_{user_id}",
                    provider_token="",
                    currency="XTR",
                    prices=[LabeledPrice(label=f"{amount} Stars", amount=amount)]
                )
            except:
                await message.answer("❌ Ошибка. Попробуй позже.")

        elif action == "open_case":
            cost = data.get("cost", 0)
            if cost > 0 and user.stars < cost:
                return await message.answer(json.dumps({"success": False, "error": "Недостаточно Stars"}))
            if cost > 0:
                user.stars -= cost

            idx = 0 if random.random() < 0.55 else 1 if random.random() < 0.80 else 2 if random.random() < 0.93 else 3 if random.random() < 0.99 else 4
            prize = prizes[idx]

            gift_id = None
            if prize["rarity"] != "Common" and available_gifts:
                gift_id = list(available_gifts.values())[0]

            item = InventoryItem(user_id=user_id, name=prize["name"], rarity=prize["rarity"], emoji=prize["emoji"], value=prize["value"], gift_id=gift_id)
            session.add(item)
            await session.commit()

            real_gift = False
            if gift_id:
                try:
                    await bot.send_gift(user_id=user_id, gift_id=gift_id)
                    real_gift = True
                except: pass

            await message.answer(json.dumps({"success": True, "prize": prize, "real_gift_sent": real_gift}))

async def main():
    await init_db()
    try:
        from aiogram.methods import GetAvailableGifts
        gifts = await bot(GetAvailableGifts())
        global available_gifts
        available_gifts = {g.name: g.id for g in gifts.gifts} if gifts.gifts else {}
    except: pass
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())