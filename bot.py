import sqlite3
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "7974172226:AAFOIPcl7LJmxJcV5rG9AnclbPqQlBvZNLo"
ADMIN_ID = 5775388579

logging.basicConfig(level=logging.INFO)

# Railway uchun xavfsiz database
conn = sqlite3.connect("kino.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
user_id INTEGER PRIMARY KEY,
premium INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS movies(
code TEXT,
file_id TEXT,
premium INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS channels(
username TEXT
)
""")

conn.commit()


# 🔥 START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    cursor.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (user_id,))
    conn.commit()

    if user_id == ADMIN_ID:

        keyboard = [
            ["🎬 Kino yuklash", "🗑 Kino o‘chirish"],
            ["📊 Foydalanuvchilar", "⭐ Premium berish"],
            ["📢 Majburiy kanal qo‘shish"]
        ]

    else:

        keyboard = [
            ["🎥 Kino ko‘rish", "⭐ Premium olish"]
        ]

    await update.message.reply_text(
        "🍿 Kino botga xush kelibsiz!",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )


# 🔥 OBUNA TEKSHIRISH
async def check_sub(bot, user_id):
    cursor.execute("SELECT username FROM channels")
    channels = cursor.fetchall()

    for ch in channels:
        try:
            member = await bot.get_chat_member(ch[0], user_id)

            if member.status not in ["member", "administrator", "creator"]:
                return ch[0]

        except:
            return ch[0]

    return None


# 🔥 MESSAGE HANDLER
async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    text = update.message.text

    # ===== ADMIN =====
    if user_id == ADMIN_ID:

        if text == "🎬 Kino yuklash":
            context.user_data["step"] = "code"
            await update.message.reply_text("Kino kodini yuboring:")

        elif context.user_data.get("step") == "code":
            context.user_data["movie_code"] = text
            context.user_data["step"] = "video"
            await update.message.reply_text("Endi kinoni VIDEO qilib yuboring.")

        elif text == "🗑 Kino o‘chirish":
            context.user_data["step"] = "delete"
            await update.message.reply_text("O‘chirmoqchi bo‘lgan kino kodini yuboring.")

        elif context.user_data.get("step") == "delete":
            cursor.execute("DELETE FROM movies WHERE code=?", (text,))
            conn.commit()
            context.user_data.clear()
            await update.message.reply_text("✅ Kino o‘chirildi.")

        elif text == "📊 Foydalanuvchilar":

            cursor.execute("SELECT user_id FROM users")
            users = cursor.fetchall()

            msg = f"👥 Jami foydalanuvchilar: {len(users)}\n\n"

            for u in users[:20]:
                msg += f"ID: {u[0]}\n"

            await update.message.reply_text(msg)

        elif text == "⭐ Premium berish":
            context.user_data["step"] = "premium"
            await update.message.reply_text("Premium bermoqchi bo‘lgan USER ID ni yuboring.")

        elif context.user_data.get("step") == "premium":

            cursor.execute("UPDATE users SET premium=1 WHERE user_id=?", (text,))
            conn.commit()

            context.user_data.clear()

            await update.message.reply_text("✅ Premium berildi.")

        elif text == "📢 Majburiy kanal qo‘shish":
            context.user_data["step"] = "channel"
            await update.message.reply_text("Kanal usernamesini yuboring.\nMasalan: @kanal")

        elif context.user_data.get("step") == "channel":

            cursor.execute("INSERT INTO channels VALUES(?)", (text,))
            conn.commit()

            context.user_data.clear()

            await update.message.reply_text("✅ Kanal qo‘shildi!")

    # ===== USER =====
    else:

        if text == "⭐ Premium olish":
            await update.message.reply_text(
                "⭐ Premium olish uchun adminga yozing:\n👉 @Sardorbeko008"
            )
            return

        if text == "🎥 Kino ko‘rish":

            channel = await check_sub(context.bot, user_id)

            if channel:
                await update.message.reply_text(
                    f"❌ Botdan foydalanish uchun {channel} kanaliga obuna bo‘ling!"
                )
                return

            await update.message.reply_text("Kino kodini yuboring:")
            return

        # Kino kodi yozilganda
        channel = await check_sub(context.bot, user_id)

        if channel:
            await update.message.reply_text(
                f"❌ Avval {channel} kanaliga obuna bo‘ling!"
            )
            return

        cursor.execute("SELECT file_id FROM movies WHERE code=?", (text,))
        movie = cursor.fetchone()

        if movie:
            await update.message.reply_video(movie[0])
        else:
            await update.message.reply_text("❌ Kino topilmadi.")


# 🔥 VIDEO HANDLER (ENG MUHIM)
async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    if context.user_data.get("step") == "video":

        file_id = update.message.video.file_id
        code = context.user_data["movie_code"]

        cursor.execute(
            "INSERT INTO movies VALUES(?,?,0)",
            (code, file_id)
        )

        conn.commit()
        context.user_data.clear()

        await update.message.reply_text("✅ Kino saqlandi!")


# 🔥 MAIN
def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VIDEO, video_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, messages))

    print("🔥 BOT ISHGA TUSHDI!")

    app.run_polling()


if __name__ == "__main__":
    main()
