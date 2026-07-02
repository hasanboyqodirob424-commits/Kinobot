import sqlite3
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from threading import Thread

# --- SOZLAMALAR ---
BOT_TOKEN = "8718031056:AAG48_k50vWlRUSF0l3UGNU-fA2DIcKwexc"
ADMIN_ID = 7677636892 
bot = telebot.TeleBot(BOT_TOKEN)

# --- RENDER UCHUN SERVER ---
app = Flask('')
@app.route('/')
def home():
    return "Bot tirik va ishlamoqda!"
def run():
    app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# --- BAZA ---
conn = sqlite3.connect("kinolar.db", check_same_thread=False)
cursor = conn.cursor()

# --- FUNKSIYALAR ---
def check_sub(user_id):
    cursor.execute("SELECT id, link FROM kanallar")
    kanallar = cursor.fetchall()
    not_subbed = []
    for ch_id, ch_link in kanallar:
        try:
            status = bot.get_chat_member(ch_id, user_id).status
            if status in ["left", "kicked"]:
                not_subbed.append((ch_id, ch_link))
        except: pass
    return not_subbed

def get_sub_keyboard(not_subbed):
    markup = InlineKeyboardMarkup()
    for ch_id, ch_link in not_subbed:
        markup.add(InlineKeyboardButton("📢 Kanalga o'tish", url=ch_link))
    markup.add(InlineKeyboardButton("✅ Obuna bo'ldim", callback_data="check_sub"))
    return markup

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub_callback(call):
    not_subbed = check_sub(call.from_user.id)
    if not not_subbed:
        bot.edit_message_text("✅ Rahmat! Endi kino kodini yuborishingiz mumkin.", call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "⚠️ Hali barcha kanallarga a'zo bo'lmadingiz!", show_alert=True)

# --- QIDIRUV VA TUGMA ---
@bot.message_handler(func=lambda msg: True)
def search_kino(message):
    # Admin bo'lsa qidiruvga ruxsat
    if message.from_user.id != ADMIN_ID:
        not_subbed = check_sub(message.from_user.id)
        if not_subbed:
            bot.send_message(message.chat.id, "⚠️ Botdan foydalanish uchun kanallarga a'zo bo'ling:", reply_markup=get_sub_keyboard(not_subbed))
            return
    
    cursor.execute("SELECT nomi, file_id FROM kinolar WHERE kod = ?", (message.text,))
    result = cursor.fetchone()
    if result:
        markup = InlineKeyboardMarkup()
        # Admin bilan bog'lanish tugmasi
        markup.add(InlineKeyboardButton("👨‍💻 Admin bilan bog'lanish", url="https://t.me/qodirov_7o7")) 
        
        caption_text = f"🎬 Nomi: {result[0]}\n🔢 Kodi: {message.text}"
        try:
            bot.send_video(message.chat.id, result[1], caption=caption_text, reply_markup=markup)
        except Exception:
            bot.send_document(message.chat.id, result[1], caption=caption_text, reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "❌ Afsuski, bu kod bilan kino topilmadi.")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
