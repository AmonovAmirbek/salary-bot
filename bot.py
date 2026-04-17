import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import asyncio

TOKEN = "8691690312:AAHQtjYjENHeYiC3C9VN_5bUnwcPFqZB7yE"
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
    end TEXT
)
""")
conn.commit()

menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🟢 Ishni boshlash")],
        [KeyboardButton(text="✏️ Edit vaqt")],
        [KeyboardButton(text="📊 Hisobot")]
    ],
    resize_keyboard=True
)

user_state = {}

def check_user(user_id):
    return user_id == ADMIN_ID

# 🌙 00:00 da avtomatik yopish
async def auto_close():
    while True:
        now = datetime.now()
        next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        wait = (next_midnight - now).total_seconds()
        await asyncio.sleep(wait)

        cursor.execute("SELECT id FROM sessions WHERE end IS NULL")
        rows = cursor.fetchall()

        for (session_id,) in rows:
            end_time = next_midnight - timedelta(seconds=1)
            cursor.execute("UPDATE sessions SET end=? WHERE id=?", (end_time.isoformat(), session_id))

        conn.commit()

@dp.message()
async def handler(msg: types.Message):
    user_id = msg.from_user.id

    if not check_user(user_id):
        await msg.answer("Sizga ruxsat yo‘q")
        return

    text = msg.text.strip()

    if text == "/start":
        await msg.answer("Ish botiga xush kelibsiz", reply_markup=menu)

    # 🟢 Ishni boshlash
    elif text == "🟢 Ishni boshlash":
        now = datetime.now()

        # agar bugun ochiq smena bo‘lsa qayta ochmasin
        cursor.execute("SELECT id FROM sessions WHERE end IS NULL AND user_id=?", (user_id,))
        active = cursor.fetchone()

        if active:
            await msg.answer("Bugungi smena allaqachon boshlangan ✅")
            return

        cursor.execute("INSERT INTO sessions (user_id, start, end) VALUES (?, ?, NULL)", (user_id, now.isoformat()))
        conn.commit()

        await msg.answer(f"🟢 Ish boshlandi: {now.strftime('%H:%M')}")

    # ✏️ Edit
    elif text == "✏️ Edit vaqt":
        user_state[user_id] = "edit_time"
        await msg.answer("Boshlanish vaqtini kiriting (HH:MM). Masalan: 09:30")

    elif user_state.get(user_id) == "edit_time":
        try:
            t = datetime.strptime(text, "%H:%M").time()
            today = datetime.now()
            new_start = today.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)

            # bugungi smenani topish
            cursor.execute("""
                SELECT id FROM sessions 
                WHERE user_id=? AND end IS NULL
                ORDER BY id DESC LIMIT 1
            """, (user_id,))
            row = cursor.fetchone()

            if row:
                cursor.execute("UPDATE sessions SET start=? WHERE id=?", (new_start.isoformat(), row[0]))
            else:
                # agar smena yo‘q bo‘lsa, yangi yaratib qo‘yadi
                cursor.execute("INSERT INTO sessions (user_id, start, end) VALUES (?, ?, NULL)", (user_id, new_start.isoformat()))

            conn.commit()
            await msg.answer(f"✏️ Boshlanish vaqti {text} ga o‘zgartirildi ✅")

        except:
            await msg.answer("❌ Format noto‘g‘ri. Masalan: 09:30")

        user_state[user_id] = None

    # 📊 Hisobot
    elif text == "📊 Hisobot":
        user_state[user_id] = "from_date"
        await msg.answer("Boshlanish sanani kiriting (YYYY-MM-DD):")

    elif user_state.get(user_id) == "from_date":
        user_state[user_id] = {"from": text}
        await msg.answer("Tugash sanani kiriting (YYYY-MM-DD):")

    elif isinstance(user_state.get(user_id), dict):
        data = user_state[user_id]

        try:
            from_date = datetime.strptime(data["from"], "%Y-%m-%d")
            to_date = datetime.strptime(text, "%Y-%m-%d") + timedelta(days=1)
        except:
            await msg.answer("❌ Sana noto‘g‘ri formatda. Masalan: 2026-04-17")
            user_state[user_id] = None
            return

        cursor.execute("SELECT start, end FROM sessions WHERE user_id=?", (user_id,))
        rows = cursor.fetchall()

        total_seconds = 0

        for start, end in rows:
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end) if end else datetime.now()

            if start_dt >= from_date and start_dt < to_date:
                sec = (end_dt - start_dt).total_seconds()
                if sec > 0:
                    total_seconds += sec

        hours = total_seconds / 3600
        salary = int(hours * RATE)

        await msg.answer(
            f"📊 HISOBOT\n\n"
            f"⏱ Soat: {hours:.2f}\n"
            f"💰 Maosh: {salary:,} so‘m"
        )

        user_state[user_id] = None


async def main():
    asyncio.create_task(auto_close())
    await dp.start_polling(bot)

asyncio.run(main())
