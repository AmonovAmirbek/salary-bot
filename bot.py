import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import asyncio

TOKEN = "8691690312:AAFyyaksYlmJt9J-vtBeZiSlECkP-p5dz8E"
ADMIN_ID = 5211995271

RATE = 20428

bot = Bot(token=TOKEN)
dp = Dispatcher()

conn = sqlite3.connect("work.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    start TEXT,
    end TEXT,
    break_seconds INTEGER DEFAULT 0,
    break_start TEXT
)
""")
conn.commit()

menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🟢 Ishni boshlash")],
        [KeyboardButton(text="⏸ Dam"), KeyboardButton(text="▶️ Davom")],
        [KeyboardButton(text="🔴 Tugatish")],
        [KeyboardButton(text="📊 Hisobot")]
    ],
    resize_keyboard=True
)

user_state = {}

def check_user(user_id):
    return user_id == ADMIN_ID

async def auto_close():
    while True:
        now = datetime.now()
        next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0)
        wait = (next_midnight - now).total_seconds()
        await asyncio.sleep(wait)

        cursor.execute("SELECT id FROM sessions WHERE end IS NULL")
        rows = cursor.fetchall()

        for row in rows:
            end_time = next_midnight - timedelta(seconds=1)
            cursor.execute("UPDATE sessions SET end=? WHERE id=?", (end_time.isoformat(), row[0]))

        conn.commit()

@dp.message()
async def handler(msg: types.Message):
    user_id = msg.from_user.id

    if not check_user(user_id):
        await msg.answer("Sizga ruxsat yo‘q")
        return

    text = msg.text

    if text == "/start":
        await msg.answer("Ish botiga xush kelibsiz", reply_markup=menu)

    elif text == "🟢 Ishni boshlash":
        now = datetime.now().isoformat()
        cursor.execute("INSERT INTO sessions (user_id, start) VALUES (?, ?)", (user_id, now))
        conn.commit()
        await msg.answer("Ish boshlandi")

    elif text == "⏸ Dam":
        now = datetime.now().isoformat()
        cursor.execute("UPDATE sessions SET break_start=? WHERE end IS NULL", (now,))
        conn.commit()
        await msg.answer("Dam boshlandi")

    elif text == "▶️ Davom":
        now = datetime.now()
        cursor.execute("SELECT id, break_start, break_seconds FROM sessions WHERE end IS NULL")
        row = cursor.fetchone()

        if row and row[1]:
            break_start = datetime.fromisoformat(row[1])
            diff = (now - break_start).total_seconds()
            total = row[2] + diff

            cursor.execute("UPDATE sessions SET break_seconds=?, break_start=NULL WHERE id=?", (total, row[0]))
            conn.commit()

            await msg.answer("Davom etildi")

    elif text == "🔴 Tugatish":
        now = datetime.now().isoformat()
        cursor.execute("UPDATE sessions SET end=? WHERE end IS NULL", (now,))
        conn.commit()
        await msg.answer("Ish tugadi")

    elif text == "📊 Hisobot":
        user_state[user_id] = "from"
        await msg.answer("Boshlanish sana (YYYY-MM-DD):")

    elif user_state.get(user_id) == "from":
        user_state[user_id] = {"from": text}
        await msg.answer("Tugash sana (YYYY-MM-DD):")

    elif isinstance(user_state.get(user_id), dict):
        data = user_state[user_id]
        from_date = datetime.strptime(data["from"], "%Y-%m-%d")
        to_date = datetime.strptime(text, "%Y-%m-%d") + timedelta(days=1)

        cursor.execute("SELECT start, end, break_seconds FROM sessions WHERE user_id=?", (user_id,))
        rows = cursor.fetchall()

        total = 0

        for start, end, br in rows:
            start = datetime.fromisoformat(start)
            end = datetime.fromisoformat(end) if end else datetime.now()

            if start >= from_date and start <= to_date:
                total += (end - start).total_seconds() - br

        hours = total / 3600
        salary = int(hours * RATE)

Amir, [17.04.2026 20:59]
await msg.answer(f"⏱ {hours:.2f} soat\n💰 {salary:,} so‘m")

        user_state[user_id] = None

async def main():
    asyncio.create_task(auto_close())
    await dp.start_polling(bot)

asyncio.run(main())
