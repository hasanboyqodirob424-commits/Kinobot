import telebot
import sqlite3
import time
from telebot import types
from flask import Flask
from threading import Thread

# --- SOZLAMALAR ---
BOT_TOKEN = "8718031056:AAFUdaSpf3aKb7FnjfGmNosfCifMbvhVykQ"
ADMIN_ID = 7677636892
ADMIN_USERNAME = "qodirov_7o7"

bot = telebot.TeleBot(BOT_TOKEN)

# --- RENDER UCHUN SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Bot ishlamoqda!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# --- BAZA ---
conn = sqlite3.connect("kinolar.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS kinolar (kod TEXT PRIMARY KEY, nomi TEXT, file_id TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS kanallar (id TEXT PRIMARY KEY, link TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS foydalanuvchilar (user_id INTEGER PRIMARY KEY)")
conn.commit()

# --- OBUNANI TEKSHIRISH ---
def check_sub(user_id):
    cursor.execute("SELECT id, link FROM kanallar")
    kanallar = cursor.fetchall()
    not_subbed = []
    for kanal_id, link in kanallar:
        try:
            if bot.get_chat_member(int(kanal_id), user_id).status in ['left', 'kicked']:
                not_subbed.append(link)
        except: pass
    return not_subbed

def get_sub_keyboard(not_subbed):
    kb = types.InlineKeyboardMarkup(row_width=1)
    for i, link in enumerate(not_subbed, start=1):
        kb.add(types.InlineKeyboardButton(f"📢 {i}-Kanalga obuna bo'lish", url=link))
    kb.add(types.InlineKeyboardButton("✅ Obuna bo'ldim", callback_data="check_sub"))
    return kb

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub_cb(call):
    if not check_sub(call.from_user.id):
        bot.edit_message_text("✅ Rahmat! Endi kino kodini yuboring.", call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "⚠️ Hali obuna bo'lmadingiz!", show_alert=True)

# --- QIDIRUV ---
@bot.message_handler(func=lambda msg: True)
def search_kino(msg):
    if msg.from_user.id != ADMIN_ID:
        subs = check_sub(msg.from_user.id)
        if subs:
            bot.send_message(msg.chat.id, "⚠️ Botdan foydalanish uchun kanallarga obuna bo'ling:", reply_markup=get_sub_keyboard(subs))
            return

    cursor.execute("SELECT nomi, file_id FROM kinolar WHERE kod = ?", (msg.text,))
    res = cursor.fetchone()
    if res:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("👨‍💻 Admin bilan bog'lanish", url=f"https://t.me/{ADMIN_USERNAME}"))
        try:
            bot.send_video(msg.chat.id, res[1], caption=f"🎬 {res[0]}\n🔢 Kod: {msg.text}", reply_markup=kb)
        except:
            bot.send_document(msg.chat.id, res[1], caption=f"🎬 {res[0]}\n🔢 Kod: {msg.text}", reply_markup=kb)
    else:
        bot.send_message(msg.chat.id, "❌ Kino topilmadi.")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
    
