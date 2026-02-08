import sqlite3
from telegram import *
from telegram.ext import *
import logging

TOKEN = "TOKENNI_SHU_YERGA"
ADMIN_ID = 5775388579

MANDATORY_CHANNEL = None

logging.basicConfig(level=logging.INFO)

conn = sqlite3.connect("kino.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS movies(
code TEXT,
file_id TEXT,
premium INTEGER
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS users(
user_id INTEGER PRIMARY KEY,
premium INTEGER DEFAULT 0
)
""")

conn.commit()


# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    c.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (user_id,))
    conn.commit()

    if user_id == ADMIN_ID:
        keyboard = [
            ["🎬 Kino yuklash", "🗑 Kino o‘chirish"],
            ["📊 Statistika", "⭐ Premium berish"],
            ["📢 Kanal qo‘shish"]
        ]
    else:
        keyboard = [
            ["🎥 Kino ko‘rish"],
            ["⭐ Premium olish"]
        ]

    await update.message.reply_text(
        "🍿 Kino botga xush kelibsiz!",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )


# MESSAGE HANDLER
async def messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global MANDATORY_CHANNEL

    text = update.message.text
    user_id = update.effective_user.id

    # ADMIN PANEL
    if user_id == ADMIN_ID:

        if text == "🎬 Kino yuklash":
            context.user_data["state"] = "code"
            await update.message.reply_text("Kino kodini yuboring:")

        elif context.user_data.get("state") == "code":
            context.user_data["movie_code"] = text
            context.user_data["state"] = "video"
            await update.message.reply_text("Endi kinoni VIDEO qilib yuboring!")

        elif text == "📢 Kanal qo‘shish":
            context.user_data["state"] = "channel"
            await update.message.reply_text("Kanal usernamesini yuboring.\nMasalan: @kanal")

        elif context.user_data.get("state") == "channel":
            MANDATORY_CHANNEL = text
            context.user_data.clear()
            await update.message.reply_text("✅ Majburiy obuna qo‘shildi!")

        elif text == "📊 Statistika":
            c.execute("SELECT COUNT(*) FROM users")
            total = c.fetchone()[0]
            await update.message.reply_text(f"👥 Jami foydalanuvchilar: {total}")

        elif text == "⭐ Premium berish":
            context.user_data["state"] = "premium"
            await update.message.reply_text("User ID yuboring:")

        elif context.user_data.get("state") == "premium":
            c.execute("UPDATE users SET premium=1 WHERE user_id=?", (text,))
            conn.commit()
            context.user_data.clear()
            await update.message.reply_text("✅ Premium berildi!")

    # FOYDALANUVCHI
    else:

        if text == "⭐ Premium olish":
            await update.message.reply_text(
                "Premium olish uchun 👉 @Sardorbeko008 ga yozing."
            )

        elif text == "🎥 Kino ko‘rish":
            await update.message.reply_text("Kino kodini yuboring:")

        else:
            # CHANNEL CHECK
            if MANDATORY_CHANNEL:
                try:
                    member = await context.bot.get_chat_member(
                        MANDATORY_CHANNEL, user_id
                    )

                    if member.status not in ["member", "administrator", "creator"]:
                        await update.message.reply_text(
                            f"❌ Botdan foydalanish uchun {MANDATORY_CHANNEL} ga obuna bo‘ling!"
                        )
                        return
                except:
                    pass

            c.execute("SELECT * FROM movies WHERE code=?", (text,))
            movie = c.fetchone()

            if movie:
                await update.message.reply_video(movie[1])
            else:
                await update.message.reply_text("❌ Kino topilmadi.")


# VIDEO HANDLER (ENG MUHIM QISM)
async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if context.user_data.get("state") == "video":

        file_id = update.message.video.file_id
        code = context.user_data["movie_code"]

        c.execute(
            "INSERT INTO movies VALUES(?,?,?)",
            (code, file_id, 0)
        )
        conn.commit()

        context.user_data.clear()

        await update.message.reply_text("✅ Kino saqlandi!")


# MAIN
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(MessageHandler(filters.VIDEO, video_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, messages))

    print("🔥 Kino bot ishga tushdi!")
    app.run_polling()


if __name__ == "__main__":
    main()
