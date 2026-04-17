import asyncio
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
import aiosqlite

from apscheduler.schedulers.asyncio import AsyncIOScheduler

TOKEN = "8691690312:AAGBqxmj14IiCfQY76oUl5wtKI907sPR_9M"

bot = Bot(token=TOKEN)
dp = Dispatcher()

DB = "work.db"


# ---------------- DATABASE ----------------
async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            start_time TEXT,
            end_time TEXT,
            duration REAL,
            status TEXT
        )
        """)
        await db.commit()


# ---------------- HELPERS ----------------
async def get_active_session(user_id):
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            "SELECT id, start_time FROM sessions WHERE user_id=? AND status='active'",
            (user_id,)
        )
        return await cursor.fetchone()


def parse_time(t):
    return datetime.fromisoformat(t)


# ---------------- START WORK ----------------
@dp.message(F.text == "🚀 Ishni boshlash")
async def start_work(message: types.Message):
    user_id = message.from_user.id

    active = await get_active_session(user_id)
    if active:
        await message.answer("⚠️ Sizda allaqachon aktiv ish sessiya bor!")
        return

    now = datetime.now().isoformat()

    async with aiosqlite.connect(DB) as db:
        await db.execute("""
            INSERT INTO sessions (user_id, start_time, status)
            VALUES (?, ?, 'active')
        """, (user_id, now))
        await db.commit()

    await message.answer(f"✅ Ish boshlandi: {now}")


# ---------------- END WORK ----------------
async def close_session(user_id, session_id, start_time):
    end = datetime.now()
    start = parse_time(start_time)

    duration = (end - start).total_seconds() / 3600

    async with aiosqlite.connect(DB) as db:
        await db.execute("""
            UPDATE sessions
            SET end_time=?, duration=?, status='closed'
            WHERE id=?
        """, (end.isoformat(), duration, session_id))
        await db.commit()


# ---------------- AUTO CLOSE AT MIDNIGHT ----------------
async def close_all_active():
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("""
            SELECT id, user_id, start_time FROM sessions
            WHERE status='active'
        """)
        rows = await cursor.fetchall()

        for session_id, user_id, start_time in rows:
            # close at midnight simulation
            await close_session(user_id, session_id, start_time)


# ---------------- BALANCE ----------------
@dp.message(F.text == "💰 Balans")
async def balance(message: types.Message):
    user_id = message.from_user.id

    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute("""
            SELECT SUM(duration) FROM sessions
            WHERE user_id=? AND status='closed'
        """, (user_id,))
        total = await cursor.fetchone()

    hours = total[0] or 0
    await message.answer(f"💰 Umumiy ish vaqtingiz: {hours:.2f} soat")


# ---------------- EDIT (simple version) ----------------
@dp.message(F.text.startswith("✏️ Edit"))
async def edit_session(message: types.Message):
    try:
        _, session_id, new_start = message.text.split()

        new_start_dt = datetime.fromisoformat(new_start)

        async with aiosqlite.connect(DB) as db:
            await db.execute("""
                UPDATE sessions
                SET start_time=?
                WHERE id=?
            """, (new_start_dt.isoformat(), session_id))
            await db.commit()

        await message.answer("✏️ Sessiya yangilandi")

    except Exception:
        await message.answer("Format: ✏️ Edit <id> <YYYY-MM-DDTHH:MM:SS>")


# ---------------- MIDNIGHT SCHEDULER ----------------
scheduler = AsyncIOScheduler()

def setup_scheduler():
    scheduler.add_job(close_all_active, "cron", hour=0, minute=0)
    scheduler.start()


# ---------------- MAIN ----------------
async def main():
    await init_db()
    setup_scheduler()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
