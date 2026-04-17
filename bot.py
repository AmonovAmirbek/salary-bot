import sqlite3
import asyncio
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

TOKEN = "8691690312:AAG-7JrXB9uskV0RnYVYdtDgzyesyK1H1sw"
ADMIN_ID = 123456789

DEFAULT_RATE = 20428

bot = Bot(token=TOKEN)
dp = Dispatcher()

# DATABASE
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
    user_id INTEGER PRIMARY KEY,
    rate INTEGER
)
""")

conn.commit()

# MENU
menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🟢 Boshlash")],
        [KeyboardButton(text="💰 Balans")],
        [KeyboardButton(text="💵 Soat narxi")]
    ],
    resize_keyboard=True
)

user_state = {}

def get_rate(user_id: int):
    cursor.execute("SELECT rate FROM settings WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else DEFAULT_RATE


# 🌙 AUTO CLOSE (00:00)
async def auto_close():
    while True:
        now = datetime.now()
        next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0)
        await asyncio.sleep((next_midnight - now).total_seconds())

        cursor.execute("SELECT id FROM sessions WHERE end IS NULL")
        rows = cursor.fetchall()

        for (sid,) in rows:
            cursor.execute(
                "UPDATE sessions SET end=? WHERE id=?",
                (next_midnight.isoformat(), sid)
            )

        conn.commit()


# HANDLER
@dp.message()
async def handler(msg: Message):
    user_id = msg.from_user.id
    text = msg.text

    # START
    if text == "/start":
        await msg.answer("Ish botga xush kelibsiz", reply_markup=menu)

    # BOSHLASH
    elif text == "🟢 Boshlash":
        now = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO sessions (user_id, start, end) VALUES (?, ?, NULL)",
            (user_id, now)
        )
        conn.commit()
        await msg.answer("Ish boshlandi")

    # BALANS
    elif text == "💰 Balans":
        cursor.execute("SELECT start, end FROM sessions WHERE user_id=?", (user_id,))
        rows = cursor.fetchall()

        total = 0

        for start, end in rows:
            start = datetime.fromisoformat(start)
            end = datetime.fromisoformat(end) if end else datetime.now()

            total += (end - start).total_seconds()

        hours = total / 3600
        rate = get_rate(user_id)
        salary = int(hours * rate)

        await msg.answer(
            f"⏱ Soat: {hours:.2f}\n"
            f"💵 Stavka: {rate}\n"
            f"💰 Maosh: {salary}"
        )

    # SOAT NARXI BOSHLASH
    elif text == "💵 Soat narxi":
        user_state[user_id] = "rate"
        await msg.answer("Yangi soat narxini kiriting:")

    # SOAT NARXI SAQLASH
    elif user_state.get(user_id) == "rate":
        try:
            rate = int(text)

            cursor.execute("INSERT OR REPLACE INTO settings (user_id, rate) VALUES (?, ?)",
                           (user_id, rate))
            conn.commit()

            user_state[user_id] = None
            await msg.answer(f"Yangi narx: {rate}")

        except:
            await msg.answer("Faqat raqam kiriting!")


async def main():
    asyncio.create_task(auto_close())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
