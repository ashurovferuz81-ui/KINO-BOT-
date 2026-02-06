import aiosqlite
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import asyncio
import subprocess
import sys
import json
import os

# ================= CONFIG =================
MASTER_TOKEN = "8511690084:AAE5bCLOO3rXwsZQNJ3JjjSmNxL-4MMlG80"
MASTER_ADMIN = 5775388579  # Sizning Telegram ID
DATABASE = "safobuilder.db"
USERS_FILE = "users.json"  # Foydalanuvchi tokenlarini saqlash

# ================= INIT =================
async def init_db():
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS movies(
            code TEXT PRIMARY KEY,
            file_id TEXT
        )
        """)
        await db.commit()

if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({}, f)

# ================= MENYU =================
user_menu = ReplyKeyboardMarkup([["🎬 Kino bot"]], resize_keyboard=True)
admin_panel_buttons = InlineKeyboardMarkup([
    [InlineKeyboardButton("➕ Kino qo‘shish", callback_data="add_movie")],
    [InlineKeyboardButton("🔙 Orqaga", callback_data="back")]
])

state = {}
user_movie_upload = {}

# ================= MASTER BOT =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id == MASTER_ADMIN:
        await update.message.reply_text("🔥 Siz master admin panelga kirdingiz!", reply_markup=admin_panel_buttons)
    else:
        await update.message.reply_text("🚀 Kino botga xush kelibsiz!", reply_markup=user_menu)

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    text = update.message.text

    if text == "🎬 Kino bot":
        await update.message.reply_text("✅ Foydalanuvchi bot tokenini yuboring:")
        state[chat_id] = "waiting_token"
        return

    if chat_id in state and state[chat_id] == "waiting_token":
        token = text.strip()
        # Foydalanuvchi botini subprocess orqali ishga tushirish
        cmd = [sys.executable, "user_bot.py", token, str(chat_id)]
        subprocess.Popen(cmd)
        # Token saqlash
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
        users[str(chat_id)] = token
        with open(USERS_FILE, "w") as f:
            json.dump(users, f)
        await update.message.reply_text("✅ Token qabul qilindi. Foydalanuvchi bot ishga tushirilmoqda...")
        state.pop(chat_id)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    if chat_id != MASTER_ADMIN:
        return

    if query.data == "add_movie":
        await query.message.reply_text("📌 Kino qo‘shish: KODni kiriting")
        state[chat_id] = "waiting_code"
    elif query.data == "back":
        await query.message.reply_text("🔙 Orqaga", reply_markup=None)

async def code_video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id != MASTER_ADMIN:
        return

    if chat_id in state and state[chat_id] == "waiting_code":
        code = update.message.text
        user_movie_upload[chat_id] = {"code": code}
        await update.message.reply_text(f"Kod saqlandi: {code}\nEndi kinoni video sifatida yuboring")
        state[chat_id] = "waiting_video"
        return

    if chat_id in state and state[chat_id] == "waiting_video":
        if update.message.video:
            code = user_movie_upload[chat_id]["code"]
            file_id = update.message.video.file_id
            async with aiosqlite.connect(DATABASE) as db:
                await db.execute("INSERT OR REPLACE INTO movies(code,file_id) VALUES(?,?)", (code, file_id))
                await db.commit()
            await update.message.reply_text(f"✅ Kino saqlandi! KOD: {code}")
            user_movie_upload.pop(chat_id)
            state.pop(chat_id)
        else:
            await update.message.reply_text("❌ Iltimos video yuboring!")

# ================= MAIN =================
async def main():
    await init_db()
    app = ApplicationBuilder().token(MASTER_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT, message))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT, code_video_handler))
    print("🔥 Master bot platforma ishladi!")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
