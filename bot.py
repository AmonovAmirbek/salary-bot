import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import asyncio

TOKEN = "8691690312:AAG2-E5EMT_LchJnGBXOcYsRvjyuwZ3Y4Z8"
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

# ---------------- MENU ----------------
menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🟢 Ishni boshlash")],
        [KeyboardButton(text="✏️ Edit vaqt")],
        [KeyboardButton(text="💰 Balans")]
    ],
    resize_keyboard=True
)

user_state = {}

def check_user(user_id):
    return user_id == ADMIN_ID


# ---------------- AUTO CLOSE ----------------
async def auto_close():
    while True:
        now = datetime.now()
        next_midnight = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        wait = (next_midnight - now).total_seconds()
        await asyncio.sleep(wait)

        end_time = next_midnight - timedelta(seconds=1)

        cursor.execute("SELECT id FROM sessions WHERE end IS NULL")
        rows = cursor.fetchall()

        for (session_id,) in rows:
            cursor.execute(
                "UPDATE sessions SET end=? WHERE id=?",
                (end_time.isoformat(), session_id)
            )

        conn.commit()


# ---------------- HANDLER ----------------
@dp.message()
async def handler(msg: types.Message):
    user_id = msg.from_user.id

    if not check_user(user_id):
        await msg.answer("Sizga ruxsat yo‘q")
        return

    text = msg.text.strip()


    # ---------------- START ----------------
    if text == "/start":
        await msg.answer("Ish botiga xush kelibsiz", reply_markup=menu)


    # ---------------- START WORK ----------------
    elif text == "🟢 Ishni boshlash":
        now = datetime.now()

        cursor.execute(
            "SELECT id FROM sessions WHERE end IS NULL AND user_id=?",
            (user_id,)
        )
        active = cursor.fetchone()

        if active:
            await msg.answer("Bugungi smena allaqachon boshlangan ✅")
            return

        cursor.execute(
            "INSERT INTO sessions (user_id, start, end) VALUES (?, ?, NULL)",
            (user_id, now.isoformat())
        )
        conn.commit()

        await msg.answer(f"🟢 Ish boshlandi: {now.strftime('%H:%M')}")


    # ---------------- EDIT ----------------
    elif text == "✏️ Edit vaqt":
        user_state[user_id] = "edit_time"
        await msg.answer("Boshlanish vaqtini kiriting (HH:MM). Masalan: 09:30")


    elif user_state.get(user_id) == "edit_time":
        try:
            t = datetime.strptime(text, "%H:%M").time()
            today = datetime.now()

            new_start = today.replace(
                hour=t.hour,
                minute=t.minute,
                second=0,
                microsecond=0
            )

            cursor.execute("""
                SELECT id FROM sessions
                WHERE user_id=? AND end IS NULL
                ORDER BY id DESC LIMIT 1
            """, (user_id,))
            row = cursor.fetchone()

            if row:
                cursor.execute(
                    "UPDATE sessions SET start=? WHERE id=?",
                    (new_start.isoformat(), row[0])
                )
            else:
                cursor.execute(
                    "INSERT INTO sessions (user_id, start, end) VALUES (?, ?, NULL)",
                    (user_id, new_start.isoformat())
                )

            conn.commit()
            await msg.answer(f"✏️ Vaqt yangilandi: {text}")

        except:
            await msg.answer("❌ Format noto‘g‘ri (HH:MM)")

        user_state[user_id] = None


    # ---------------- BALANCE (NEW) ----------------
    elif text == "💰 Balans":

        cursor.execute(
            "SELECT start, end FROM sessions WHERE user_id=?",
            (user_id,)
        )
        rows = cursor.fetchall()

        total_seconds = 0

        for start, end in rows:
            start_dt = datetime.fromisoformat(start)

            # agar hali ochiq bo‘lsa
            if end is None:
                end_dt = datetime.now()
            else:
                end_dt = datetime.fromisoformat(end)

            sec = (end_dt - start_dt).total_seconds()
            if sec > 0:
                total_seconds += sec

        hours = total_seconds / 3600
        salary = int(hours * RATE)

        await msg.answer(
            "💰 BALANS\n\n"
            f"⏱ Umumiy vaqt: {hours:.2f} soat\n"
            f"💸 Hisoblangan pul: {salary:,} so‘m"
        )


# ---------------- MAIN ----------------
async def main():
    asyncio.create_task(auto_close())
    await dp.start_polling(bot)


asyncio.run(main())
