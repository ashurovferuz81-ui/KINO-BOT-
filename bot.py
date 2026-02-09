import sqlite3
import nest_asyncio
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

nest_asyncio.apply()

TOKEN = "7974172226:AAFOIPcl7LJmxJcV5rG9AnclbPqQlBvZNLo"
ADMIN_ID = 5775388579


# ===== DATABASE =====
conn = sqlite3.connect("pro_kino.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("CREATE TABLE IF NOT EXISTS movies(code TEXT PRIMARY KEY, file_id TEXT, name TEXT)")
cur.execute("CREATE INDEX IF NOT EXISTS idx_code ON movies(code)")

cur.execute("CREATE TABLE IF NOT EXISTS users(user_id INTEGER PRIMARY KEY)")
cur.execute("CREATE TABLE IF NOT EXISTS channels(channel_id TEXT PRIMARY KEY)")
cur.execute("CREATE TABLE IF NOT EXISTS vip(user_id INTEGER PRIMARY KEY)")

conn.commit()


# ===== ADMIN KEYBOARD =====
admin_keyboard = ReplyKeyboardMarkup([
    ["🎬 Kino qo‘shish", "🗑 Kino o‘chirish"],
    ["📢 Kanal qo‘shish", "❌ Kanal o‘chirish"],
    ["🚀 Reklama yuborish"],
    ["👑 VIP berish"],
    ["📊 Statistika"]
], resize_keyboard=True)


# ===== CHECK SUB =====
async def check_sub(user_id, context):
    cur.execute("SELECT channel_id FROM channels")
    channels = cur.fetchall()

    for ch in channels:
        try:
            member = await context.bot.get_chat_member(ch[0], user_id)

            if member.status in ["left", "kicked"]:
                return False
        except:
            return False

    return True


# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    cur.execute("INSERT OR IGNORE INTO users VALUES(?)", (user_id,))
    conn.commit()

    if user_id == ADMIN_ID:
        await update.message.reply_text("🔥 PRO ADMIN PANEL", reply_markup=admin_keyboard)
        return

    if not await check_sub(user_id, context):

        cur.execute("SELECT channel_id FROM channels")
        channels = cur.fetchall()

        buttons = []

        for ch in channels:
            try:
                chat = await context.bot.get_chat(ch[0])

                if chat.username:
                    url = f"https://t.me/{chat.username}"
                    buttons.append([InlineKeyboardButton("📢 Kanalga kirish", url=url)])
            except:
                pass

        buttons.append([InlineKeyboardButton("✅ Obuna bo‘ldim", callback_data="sub")])

        await update.message.reply_text(
            "📢 Avval kanallarga obuna bo‘ling:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    await update.message.reply_text("🎬 Kino kodini yuboring:")


# ===== BUTTON =====
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if await check_sub(query.from_user.id, context):
        await query.message.edit_text("✅ Obuna tasdiqlandi!\nKino kodini yuboring.")
    else:
        await query.answer("❌ Hali obuna emassiz!", show_alert=True)


# ===== VIDEO =====
async def video(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    if context.user_data.get("step") == "video":
        context.user_data["file"] = update.message.video.file_id
        context.user_data["step"] = "name"
        await update.message.reply_text("Kino nomini yozing:")


# ===== TEXT =====
async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id
    msg = update.message.text
    step = context.user_data.get("step")

    # ===== ADMIN =====
    if user_id == ADMIN_ID:

        if msg == "🎬 Kino qo‘shish":
            context.user_data["step"] = "code"
            await update.message.reply_text("Kino kodini yuboring:")
            return

        if step == "code":
            context.user_data["code"] = msg
            context.user_data["step"] = "video"
            await update.message.reply_text("Videoni yuboring:")
            return

        if step == "name":
            cur.execute("INSERT OR REPLACE INTO movies VALUES(?,?,?)",
                        (context.user_data["code"], context.user_data["file"], msg))
            conn.commit()
            context.user_data.clear()
            await update.message.reply_text("✅ Kino saqlandi!", reply_markup=admin_keyboard)
            return

        if msg == "🗑 Kino o‘chirish":
            context.user_data["step"] = "del"
            await update.message.reply_text("Kino kodini yuboring:")
            return

        if step == "del":
            cur.execute("DELETE FROM movies WHERE code=?", (msg,))
            conn.commit()
            context.user_data.clear()
            await update.message.reply_text("✅ Kino o‘chirildi!", reply_markup=admin_keyboard)
            return

        if msg == "📢 Kanal qo‘shish":
            context.user_data["step"] = "channel"
            await update.message.reply_text("@username yuboring (bot admin bo‘lsin)")
            return

        if step == "channel":
            chat = await context.bot.get_chat(msg)
            cur.execute("INSERT OR IGNORE INTO channels VALUES(?)", (str(chat.id),))
            conn.commit()
            context.user_data.clear()
            await update.message.reply_text("✅ Kanal qo‘shildi!", reply_markup=admin_keyboard)
            return

        if msg == "👑 VIP berish":
            context.user_data["step"] = "vip"
            await update.message.reply_text("User ID yuboring:")
            return

        if step == "vip":
            cur.execute("INSERT OR IGNORE INTO vip VALUES(?)", (msg,))
            conn.commit()
            context.user_data.clear()
            await update.message.reply_text("✅ VIP berildi!", reply_markup=admin_keyboard)
            return

        if msg == "🚀 Reklama yuborish":
            context.user_data["step"] = "ads"
            await update.message.reply_text("Xabar yuboring:")
            return

        if step == "ads":
            cur.execute("SELECT user_id FROM users")
            users = cur.fetchall()

            for u in users:
                try:
                    await context.bot.send_message(u[0], msg)
                except:
                    pass

            context.user_data.clear()
            await update.message.reply_text("✅ Yuborildi!", reply_markup=admin_keyboard)
            return

        if msg == "📊 Statistika":
            cur.execute("SELECT COUNT(*) FROM users")
            u = cur.fetchone()[0]

            cur.execute("SELECT COUNT(*) FROM movies")
            m = cur.fetchone()[0]

            await update.message.reply_text(f"👥 Users: {u}\n🎬 Kinolar: {m}", reply_markup=admin_keyboard)
            return

    # ===== USER =====
    if not await check_sub(user_id, context):
        await update.message.reply_text("❌ Avval obuna bo‘ling! /start")
        return

    cur.execute("SELECT file_id,name FROM movies WHERE code=?", (msg,))
    movie = cur.fetchone()

    if movie:
        await update.message.reply_video(movie[0], caption=f"🎬 {movie[1]}")
    else:
        await update.message.reply_text("❌ Kino topilmadi!")


# ===== MAIN =====
def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button, pattern="sub"))

    app.add_handler(MessageHandler(filters.VIDEO, video))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))

    print("🔥 PRO KINOBOT ISHLADI!")

    app.run_polling()


if __name__ == "__main__":
    main()
