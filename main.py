import sqlite3
import telebot
import time
from telebot import types
from flask import Flask
from threading import Thread

BOT_TOKEN = "8718031056:AAFUdaSpf3aKb7FnjfGmNosfCifMbvhVykQ"
ADMIN_ID = 7677636892
ADMIN_USERNAME = "qodirov_7o7"

bot = telebot.TeleBot(BOT_TOKEN)

# --- FLASK VEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Bot tirik va ishlamoqda!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive():
    t = Thread(target=run)
    t.start()

# --- MA'LUMOTLAR BAZASI ---
conn = sqlite3.connect("kinolar.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS kinolar (kod TEXT PRIMARY KEY, nomi TEXT, file_id TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS kanallar (id TEXT PRIMARY KEY, link TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS foydalanuvchilar (user_id INTEGER PRIMARY KEY)")
conn.commit()

# --- ADMIN KLAVIATURASI ---
admin_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
admin_keyboard.add(
    types.KeyboardButton("🎬 Kino qo'shish"), types.KeyboardButton("🗑 Kino o'chirish"),
    types.KeyboardButton("📢 Kanal qo'shish"), types.KeyboardButton("❌ Kanal o'chirish"),
    types.KeyboardButton("📊 Statistika"), types.KeyboardButton("📜 Kinolar ro'yxati"),
    types.KeyboardButton("✉️ Xabar yuborish")
)

# --- JONLI OBUNANI TEKSHIRISH ---
def check_sub(user_id):
    cursor.execute("SELECT id, link FROM kanallar")
    kanallar = cursor.fetchall()
    not_subbed = []
    for kanal_id, link in kanallar:
        try:
            status = bot.get_chat_member(int(kanal_id), user_id).status
            if status in ['left', 'kicked']:
                not_subbed.append(link)
        except Exception: pass
    return not_subbed

def get_sub_keyboard(not_subbed):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for i, link in enumerate(not_subbed, start=1):
        keyboard.add(types.InlineKeyboardButton(text=f"📢 {i}-Kanalga a'zo bo'lish", url=link))
    keyboard.add(types.InlineKeyboardButton(text="✅ Obuna bo'ldim", callback_data="check_sub"))
    return keyboard

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub_callback(call):
    if not check_sub(call.from_user.id):
        bot.edit_message_text("✅ Rahmat! Endi kino kodini yuborishingiz mumkin.", call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "⚠️ Hali barcha kanallarga a'zo bo'lmadingiz!", show_alert=True)

# --- START BUYRUG'I ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    cursor.execute("INSERT OR IGNORE INTO foydalanuvchilar VALUES (?)", (message.from_user.id,))
    conn.commit()
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "Xush kelibsiz Admin!", reply_markup=admin_keyboard)
        return

    not_subbed = check_sub(message.from_user.id)
    if not_subbed:
        bot.send_message(message.chat.id, "⚠️ Botdan foydalanish uchun kanallarga a'zo bo'ling:", reply_markup=get_sub_keyboard(not_subbed))
    else:
        bot.send_message(message.chat.id, "✅ Rahmat! Endi kino kodini yuborishingiz mumkin.")

# --- ADMIN PANEL & KINO/KANAL FUNKSIYALARI (Qisqartirilgan) ---
# (Sizning asl kodingizdagi ADMIN qismi o'zgarishsiz qoldi, faqat pastdagi search_kino qismini yangiladik)

@bot.message_handler(commands=['admin'])
def admin_cmd(message):
    if message.from_user.id == ADMIN_ID: bot.send_message(message.chat.id, "Admin Panel:", reply_markup=admin_keyboard)

@bot.message_handler(func=lambda msg: msg.text in ["🎬 Kino qo'shish", "🗑 Kino o'chirish", "📢 Kanal qo'shish", "❌ Kanal o'chirish", "📊 Statistika", "📜 Kinolar ro'yxati", "✉️ Xabar yuborish"] and msg.from_user.id == ADMIN_ID)
def admin_panel_handler(message):
    # Bu yerga o'z kodingizdagi admin funksiyalarini (start_add_kino, va h.k.) qo'shib qo'ying
    pass

# --- FOYDALANUVCHILAR UCHUN QIDIRUV ---
@bot.message_handler(func=lambda msg: True)
def search_kino(message):
    not_subbed = check_sub(message.from_user.id)
    if not_subbed:
        bot.send_message(message.chat.id, "⚠️ Botdan foydalanish uchun kanallarga a'zo bo'ling:", reply_markup=get_sub_keyboard(not_subbed))
        return
    
    cursor.execute("SELECT nomi, file_id FROM kinolar WHERE kod = ?", (message.text,))
    result = cursor.fetchone()
    if result:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("👨‍💻 Admin bilan bog'lanish", url=f"https://t.me/{ADMIN_USERNAME}"))
        caption_text = f"🎬 Nomi: {result[0]}\n🔢 Kodi: {message.text}"
        try:
            bot.send_video(message.chat.id, result[1], caption=caption_text, reply_markup=markup)
        except:
            bot.send_document(message.chat.id, result[1], caption=caption_text, reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "❌ Afsuski, bu kod bilan kino topilmadi.")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
    
