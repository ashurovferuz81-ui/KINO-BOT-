import sys
import asyncio
import aiosqlite
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

DATABASE = "safobuilder.db"

token = sys.argv[1]
admin_id = int(sys.argv[2])
state = {}
user_movie_upload = {}

async def user_kino_bot():
    app = ApplicationBuilder().token(token).build()

    admin_panel = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Kino qo‘shish", callback_data="add_movie")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="back")]
    ])

    async def user_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.message.chat_id
        if chat_id == admin_id and update.message.text == "/panel":
            await update.message.reply_text("🔑 Admin panel", reply_markup=admin_panel)
            return

        if update.message.text and update.message.text.startswith("/movie"):
            try:
                code = update.message.text.split(" ")[1]
            except:
                await update.message.reply_text("❌ Xato format! /movie KOD")
                return
            async with aiosqlite.connect(DATABASE) as db:
                cursor = await db.execute("SELECT file_id FROM movies WHERE code=?", (code,))
                row = await cursor.fetchone()
                if row:
                    await context.bot.send_video(chat_id, row[0])
                else:
                    await update.message.reply_text("❌ Kino topilmadi!")

    async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        chat_id = query.message.chat_id
        if chat_id != admin_id:
            return
        if query.data == "add_movie":
            await query.message.reply_text("📌 Kino qo‘shish: KODni kiriting")
            state[chat_id] = "waiting_code_user"
        elif query.data == "back":
            await query.message.reply_text("🔙 Orqaga", reply_markup=None)

    async def code_video_handler_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
        chat_id = update.message.chat_id
        if chat_id != admin_id:
            return
        if chat_id in state and state[chat_id] == "waiting_code_user":
            code = update.message.text
            user_movie_upload[chat_id] = {"code": code}
            await update.message.reply_text(f"Kod saqlandi: {code}\nEndi kinoni video sifatida yuboring")
            state[chat_id] = "waiting_video_user"
            return
        if chat_id in state and state[chat_id] == "waiting_video_user":
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

    app.add_handler(MessageHandler(filters.TEXT, user_handler))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT, code_video_handler_user))

    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(user_kino_bot())
