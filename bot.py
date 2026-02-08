import sqlite3
import os
from telegram import *
from telegram.ext import *

TOKEN = "7974172226:AAFOIPcl7LJmxJcV5rG9AnclbPqQlBvZNLo"
ADMIN_ID = 5775388579

DB = "kino.db"

conn = sqlite3.connect(DB, check_same_thread=False)
c = conn.cursor()

# --- TABLES ---
c.execute("""CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY,
name TEXT,
premium INTEGER DEFAULT 0
)""")

c.execute("""CREATE TABLE IF NOT EXISTS movies(
code TEXT,
file_id TEXT,
premium INTEGER
)""")

c.execute("""CREATE TABLE IF NOT EXISTS channel(
username TEXT
)""")

conn.commit()


# ================= USERS =================

def add_user(user):
    c.execute("INSERT OR IGNORE INTO users(id,name) VALUES(?,?)",
              (user.id, user.first_name))
    conn.commit()


async def is_subscribed(bot, user_id):
    c.execute("SELECT username FROM channel")
    channels = c.fetchall()

    if not channels:
        return True

    for ch in channels:
        try:
            member = await bot.get_chat_member(ch[0], user_id)
            if member.status not in ["member","administrator","creator"]:
                return False
        except:
            return False

    return True


# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user)

    if user.id == ADMIN_ID:
        keyboard = [
            ["👥 Foydalanuvchilar","📊 Statistika"],
            ["🎬 Kino qo‘shish","💎 Premium kino"],
            ["➕ Kanal qo‘shish","❌ Kanal o‘chirish"],
            ["👑 Premium berish"]
        ]

        await update.message.reply_text(
            "👑 ADMIN PANEL",
            reply_markup=ReplyKeyboardMarkup(keyboard,resize_keyboard=True)
        )
        return

    # USER CHECK SUB
    if not await is_subscribed(context.bot, user.id):

        c.execute("SELECT username FROM channel")
        channels = c.fetchall()

        buttons = []

        for ch in channels:
            link = f"https://t.me/{ch[0].replace('@','')}"
            buttons.append([InlineKeyboardButton("📢 Kanalga kirish",url=link)])

        buttons.append([InlineKeyboardButton("✅ Obuna bo‘ldim",callback_data="check_sub")])

        await update.message.reply_text(
            "❗ Botdan foydalanish uchun kanalga obuna bo‘ling!",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    await update.message.reply_text("🎬 Kino kodini yuboring!")


# ================= CHECK SUB =================

async def button(update: Update, context):
    query = update.callback_query
    user = query.from_user

    if query.data == "check_sub":

        if await is_subscribed(context.bot, user.id):
            await query.edit_message_text("✅ Obuna tasdiqlandi!\n\n🎬 Endi kino kodini yuboring!")
        else:
            await query.answer("❌ Hali obuna bo‘lmadingiz!",show_alert=True)


# ================= ADMIN PANEL =================

async def admin_text(update: Update, context):
    if update.effective_user.id != ADMIN_ID:
        return

    txt = update.message.text

    if txt == "👥 Foydalanuvchilar":
        c.execute("SELECT * FROM users")
        users = c.fetchall()

        msg = f"👥 Jami: {len(users)} ta\n\n"

        for u in users[:20]:
            msg += f"{u[1]} | {u[0]}\n"

        await update.message.reply_text(msg)


    elif txt == "📊 Statistika":
        c.execute("SELECT COUNT(*) FROM users")
        total = c.fetchone()[0]

        c.execute("SELECT COUNT(*) FROM users WHERE premium=1")
        premium = c.fetchone()[0]

        await update.message.reply_text(
            f"📊 Statistika\n\nUsers: {total}\nPremium: {premium}"
        )


    elif txt == "➕ Kanal qo‘shish":
        await update.message.reply_text("Kanal username yuboring:\nMasalan 👉 @kinolar")
        context.user_data["add_channel"]=True


    elif txt == "❌ Kanal o‘chirish":
        c.execute("DELETE FROM channel")
        conn.commit()
        await update.message.reply_text("✅ Kanal o‘chirildi")


    elif txt == "👑 Premium berish":
        await update.message.reply_text("User ID yuboring:")
        context.user_data["premium"]=True


    elif txt == "🎬 Kino qo‘shish":
        await update.message.reply_text("Kino kodini yuboring:")
        context.user_data["movie"]=0


    elif txt == "💎 Premium kino":
        await update.message.reply_text("Premium kino kodini yuboring:")
        context.user_data["movie"]=1


# ================= HANDLE ADMIN STATES =================

async def admin_states(update: Update, context):

    if update.effective_user.id != ADMIN_ID:
        return

    if context.user_data.get("add_channel"):
        c.execute("DELETE FROM channel")
        c.execute("INSERT INTO channel VALUES(?)",(update.message.text,))
        conn.commit()

        context.user_data.clear()

        await update.message.reply_text("✅ Kanal qo‘shildi!")
        return


    if context.user_data.get("premium"):
        uid = int(update.message.text)
        c.execute("UPDATE users SET premium=1 WHERE id=?",(uid,))
        conn.commit()

        context.user_data.clear()

        await update.message.reply_text("✅ Premium berildi!")
        return


    if "movie" in context.user_data:

        context.user_data["code"]=update.message.text
        await update.message.reply_text("Endi kinoni VIDEO qilib yuboring!")
        context.user_data["await_video"]=True
        return


    if context.user_data.get("await_video"):

        video = update.message.video.file_id
        code = context.user_data["code"]
        premium = context.user_data["movie"]

        c.execute("INSERT INTO movies VALUES(?,?,?)",(code,video,premium))
        conn.commit()

        context.user_data.clear()

        await update.message.reply_text("✅ Kino saqlandi!")
        return


# ================= MOVIE GET =================

async def get_movie(update: Update, context):

    user = update.effective_user
    txt = update.message.text

    if user.id == ADMIN_ID:
        return

    if not await is_subscribed(context.bot, user.id):
        return

    c.execute("SELECT premium FROM users WHERE id=?",(user.id,))
    row = c.fetchone()
    premium_user = row[0] if row else 0

    c.execute("SELECT * FROM movies WHERE code=?",(txt,))
    movie = c.fetchone()

    if not movie:
        await update.message.reply_text("❌ Kino topilmadi")
        return

    if movie[2] == 1 and not premium_user:
        await update.message.reply_text(
            "💎 Premium kino!\nSotib olish 👉 @Sardorbeko008"
        )
        return

    await update.message.reply_video(movie[1])


# ================= MAIN =================

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start",start))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_states))
app.add_handler(MessageHandler(filters.VIDEO, admin_states))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_movie))

print("🔥 Kino bot ishga tushdi!")
app.run_polling()
