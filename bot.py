import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import asyncio

TOKEN = "8691690312:AAHxKA8Vb10Lv5228PrGMS7YoDUvXxvNY0Q"
ADMIN_ID = 123456789 

DEFAULT_RATE = 20428

bot = Bot(token=TOKEN)
dp = Dispatcher()

conn = sqlite3.connect("work.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    start TEXT,
    end TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS settings (
    user_id INTEGER,
    rate INTEGER
)
""")

conn.commit()

# 🔥 TUGMALAR
menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🟢 Boshlash / Начать")],
        [KeyboardButton(text="💰 Mening balansim / Мой баланс")],
        [KeyboardButton(text="✏️ O‘zgartirish / Изменить")]
    ],
    resize_keyboard=True
)

user_state = {}

def get_rate(user_id):
    cursor.execute("SELECT rate FROM settings WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else DEFAULT_RATE

# 🌙 00:00 AUTO CLOSE
async def auto_close():
    while True:
        now = datetime.now()
        next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0)
        await asyncio.sleep((next_midnight - now).total_seconds())

        cursor.execute("SELECT id FROM sessions WHERE end IS NULL")
        rows = cursor.fetchall()

        for row in rows:
            end_time = next_midnight - timedelta(seconds=1)
            cursor.execute("UPDATE sessions SET end=? WHERE id=?", (end_time.isoformat(), row[0]))

        conn.commit()

@dp.message()
async def handler(msg: types.Message):
    user_id = msg.from_user.id

    text = msg.text

    # 🔰 START
    if text == "/start":
        await msg.answer(
            "━━━━━━━━━━━━━━━\n"
            "💼 *S H I F T P A Y*\n"
            "━━━━━━━━━━━━━━━\n\n"
            "⏱ Ish vaqtingiz avtomatik hisoblanadi\n"
            "🌙 00:00 da yopiladi\n"
            "💰 Maoshingizni real vaqtda ko‘rasiz\n\n"
            "👇 Tugmani bosing",
            parse_mode="Markdown",
            reply_markup=menu
        )

    # 🟢 BOSHLASH
    elif text == "🟢 Boshlash / Начать":
        now = datetime.now().isoformat()
        cursor.execute("INSERT INTO sessions (user_id, start) VALUES (?, ?)", (user_id, now))
        conn.commit()

        await msg.answer("🚀 Ish boshlandi / Работа началась")

    # 💰 BALANS
    elif text == "💰 Mening balansim / Мой баланс":
        cursor.execute("SELECT start, end FROM sessions WHERE user_id=?", (user_id,))
        rows = cursor.fetchall()

        total_seconds = 0

        for start, end in rows:
            start = datetime.fromisoformat(start)
            end = datetime.fromisoformat(end) if end else datetime.now()

            midnight = start.replace(hour=23, minute=59, second=59)
            if end > midnight:
                end = midnight

            total_seconds += (end - start).total_seconds()

        hours = total_seconds / 3600
        rate = get_rate(user_id)
        salary = int(hours * rate)

        await msg.answer(
            "━━━━━━━━━━━━━━━\n"
            "💰  *M E N I N G   B A L A N S I M*\n"
            "━━━━━━━━━━━━━━━\n\n"
            f"⏱ Ish vaqti: *{hours:.2f} soat*\n"
            f"💵 Soat narxi: *{rate:,} so‘m*\n"
            f"💰 Jami: *{salary:,} so‘m*\n\n"
            "━━━━━━━━━━━━━━━\n"
            "🔥 Zo‘r ishlayapsiz!",
            parse_mode="Markdown"
        )

    # ✏️ RATE O‘ZGARTIRISH
    elif text == "✏️ O‘zgartirish / Изменить":
        user_state[user_id] = "rate"
        await msg.answer("💰 Yangi soat narxini kiriting:")

    elif user_state.get(user_id) == "rate":
        new_rate = int(text)

        cursor.execute("DELETE FROM settings WHERE user_id=?", (user_id,))
        cursor.execute("INSERT INTO settings VALUES (?, ?)", (user_id, new_rate))
        conn.commit()

        user_state[user_id] = None

        await msg.answer(f"✅ Yangilandi\n💰 {new_rate:,} so‘m")

async def main():
    asyncio.create_task(auto_close())
    await dp.start_polling(bot)

asyncio.run(main())
