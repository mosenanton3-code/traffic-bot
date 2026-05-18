import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ChatJoinRequest, InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "7793956570:AAGrWA34JMHjCSS6YS05AQa-w97j5nn8Nvk"
CHANNEL_ID = -1006734850777
ADMIN_IDS = [6734850777]

TEXT_JOIN_REQUEST = "👋 Привет! Твоя заявка получена.\n \n🔥 Анти-спам проверка.\n \nНажми кнопку ниже, чтобы подтвердить что ты живой человек 👇"
TEXT_VERIFIED = "✅ Спасибо! ❤️ Проверка пройдена.\n \nТвоя заявка отправлена на рассмотрение администратору.\n \nСкоро тебя одобрят — ожидай! 🎉"
TEXT_START = "👋 Привет!\n \nЕсли ты подал заявку на вступление в канал — нажми кнопку ниже 👇"
TEXT_ALREADY_VERIFIED = "✅ Ты уже верифицирован!"
TEXT_NO_REQUEST = "❌ Заявка не найдена. Сначала подай заявку на вступление в канал."

def verify_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я не бот", callback_data="verify")]
    ])

def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, username TEXT,
        status TEXT DEFAULT 'pending',
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    conn.commit()
    conn.close()

def add_user(user_id, username):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, status) VALUES (?, ?, 'pending')", (user_id, username))
    conn.commit()
    conn.close()

def get_user_status(user_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def set_verified(user_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET status = 'verified' WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_all_verified():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE status = 'verified'")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

def get_stats():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'pending'")
    pending = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE status = 'verified'")
    verified = cursor.fetchone()[0]
    conn.close()
    return pending, verified

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.chat_join_request()
async def on_join_request(request: ChatJoinRequest):
    user_id = request.from_user.id
    username = request.from_user.username or request.from_user.first_name
    add_user(user_id, username)
    try:
        await bot.send_message(chat_id=user_id, text=TEXT_JOIN_REQUEST, reply_markup=verify_keyboard())
    except Exception as e:
        logging.warning(f"Не могу написать {user_id}: {e}")

@dp.message(Command("start"))
async def on_start(message: types.Message):
    await message.answer(TEXT_START, reply_markup=verify_keyboard())

@dp.message(Command("verify"))
async def on_verify(message: types.Message):
    user_id = message.from_user.id
    status = get_user_status(user_id)
    if status == "verified":
        await message.answer(TEXT_ALREADY_VERIFIED)
        return
    if status != "pending":
        await message.answer(TEXT_NO_REQUEST)
        return
    set_verified(user_id)
    await message.answer(TEXT_VERIFIED)

@dp.callback_query(F.data == "verify")
async def on_verify_button(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    status = get_user_status(user_id)
    if status == "verified":
        await callback.answer("Ты уже верифицирован! ✅")
        return
    if status != "pending":
        await callback.answer("Заявка не найдена.", show_alert=True)
        return
    set_verified(user_id)
    await callback.message.edit_text(TEXT_VERIFIED)

@dp.message(Command("broadcast"))
async def on_broadcast(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    text = message.text.removeprefix("/broadcast").strip()
    if not text:
        await message.answer("Использование: /broadcast Текст")
        return
    users = get_all_verified()
    if not users:
        await message.answer("Нет пользователей для рассылки.")
        return
    await message.answer(f"⏳ Рассылка для {len(users)} пользователей...")
    success, failed = 0, 0
    for uid in users:
        try:
            await bot.send_message(chat_id=uid, text=text)
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
    await message.answer(f"✅ Разослано: {success}\n❌ Не доставлено: {failed}")

@dp.message(Command("stats"))
async def on_stats(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    pending, verified = get_stats()
    await message.answer(f"📊 Статистика:\n⏳ Ожидают: {pending}\n✅ Верифицированы: {verified}\n👥 Всего: {pending + verified}")

async def main():
    init_db()
    me = await bot.get_me()
    logging.info(f"Бот @{me.username} запущен!")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
