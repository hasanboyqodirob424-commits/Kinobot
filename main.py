import telebot
import sqlite3
import time
from telebot import types
from flask import Flask
from threading import Thread

# Sizning bot tokeningiz va ma'lumotlaringiz muvaffaqiyatli joylandi!
BOT_TOKEN = "8718031056:AAFUdaSpf3aKb7FnjfGmNosfCifMbvhVykQ"
ADMIN_ID = 7677636892
ADMIN_USERNAME = "qodirov_7o7"

bot = telebot.TeleBot(BOT_TOKEN)

# --- FLASK VEB SERVER (RENDER UCHUN) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot tirik va ishlamoqda!"

def run():
    app.run(host='0.0.0.0', port=8080)

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

# --- JONLI OBUNANI TEKSHIRISH TIZIMI ---
def check_sub(user_id):
    cursor.execute("SELECT id, link FROM kanallar")
    kanallar = cursor.fetchall()
    not_subbed = []
    
    for kanal_id, link in kanallar:
        try:
            status = bot.get_chat_member(int(kanal_id), user_id).status
            if status in ['left', 'kicked']:
                not_subbed.append(link)
        except Exception:
            pass
    return not_subbed

def get_sub_keyboard(not_subbed):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for i, link in enumerate(not_subbed, start=1):
        keyboard.add(types.InlineKeyboardButton(text=f"📢 {i}-Kanalga a'zo bo'lish", url=link))
    keyboard.add(types.InlineKeyboardButton(text=f"🤷‍♂️ Admin bilan bog'lanish", url=f"https://t.me/{ADMIN_USERNAME}"))
    return keyboard

# --- START BUYRUG'I ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    try:
        cursor.execute("INSERT OR IGNORE INTO foydalanuvchilar VALUES (?)", (message.from_user.id,))
        conn.commit()
    except Exception:
        pass

    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "Xush kelibsiz Admin! Panelni ochish uchun /admin deb yozing.")
        return

    not_subbed = check_sub(message.from_user.id)
    if not_subbed:
        bot.send_message(
            message.chat.id, 
            "Salom! Kino botga xush kelibsiz.\n\n⚠️ Botdan foydalanish uchun homiy kanallarga a'zo bo'lishingiz shart. A'zo bo'lib, qaytadan /start bosing!", 
            reply_markup=get_sub_keyboard(not_subbed)
        )
    else:
        bot.send_message(
            message.chat.id, 
            "✅ Rahmat! Endi kino kodini yuborishingiz mumkin. Men uni darhol topib beraman!",
            reply_markup=types.ReplyKeyboardRemove()
        )

# --- ADMIN PANEL ---
@bot.message_handler(commands=['admin'])
def admin_cmd(message):
    if message.from_user.id == ADMIN_ID:
        bot.send_message(message.chat.id, "Xush kelibsiz Admin! Kerakli bo'limni tanlang:", reply_markup=admin_keyboard)
    else:
        bot.send_message(message.chat.id, "Siz admin emassiz! ❌")

# --- ADMIN: XABAR YUBORISH ---
@bot.message_handler(func=lambda msg: msg.text == "✉️ Xabar yuborish" and msg.from_user.id == ADMIN_ID)
def start_reklama(message):
    sent = bot.send_message(message.chat.id, "Foydalanuvchilarga yubormoqchi bo'lgan xabaringizni kiriting:")
    bot.register_next_step_handler(sent, send_reklama_to_all)

def send_reklama_to_all(message):
    cursor.execute("SELECT user_id FROM foydalanuvchilar")
    users = cursor.fetchall()
    if not users:
        bot.send_message(message.chat.id, "Bazada foydalanuvchilar yo'q.")
        return
    status_msg = bot.send_message(message.chat.id, f"📢 Xabar yuborish boshlandi...")
    success, failed = 0, 0
    for user in users:
        try:
            bot.copy_message(chat_id=user[0], from_chat_id=message.chat.id, message_id=message.message_id)
            success += 1
            time.sleep(0.05)
        except Exception:
            failed += 1
    bot.edit_message_text(chat_id=message.chat.id, message_id=status_msg.message_id, text=f"📊 **Yuborildi:** {success} ta | **Bloklangan:** {failed} ta")

# --- ADMIN: KINO AMALLARI ---
@bot.message_handler(func=lambda msg: msg.text == "🎬 Kino qo'shish" and msg.from_user.id == ADMIN_ID)
def start_add_kino(message):
    sent = bot.send_message(message.chat.id, "Yangi kino uchun kod kiriting:")
    bot.register_next_step_handler(sent, save_kino_code)

def save_kino_code(message):
    kino_kod = message.text
    sent = bot.send_message(message.chat.id, f"Kod qabul qilindi: {kino_kod}\n\nEndi kino nomini kiriting:")
    bot.register_next_step_handler(sent, save_kino_name, kino_kod)

def save_kino_name(message, kino_kod):
    kino_nomi = message.text
    sent = bot.send_message(message.chat.id, f"Kino nomi qabul qilindi: {kino_nomi}\n\nEndi videoni yuboring:")
    bot.register_next_step_handler(sent, save_kino_file, kino_kod, kino_nomi)

def save_kino_file(message, kino_kod, kino_nomi):
    file_id = message.video.file_id if message.video else (message.document.file_id if message.document else None)
    if not file_id:
        bot.send_message(message.chat.id, "❌ Faqat video yoki fayl yuboring!")
        return
    try:
        cursor.execute("INSERT INTO kinolar VALUES (?, ?, ?)", (kino_kod, kino_nomi, file_id))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ Kino saqlandi!\n🔢 Kod: {kino_kod}\n🎬 Nomi: {kino_nomi}")
    except sqlite3.IntegrityError:
        bot.send_message(message.chat.id, "❌ Bu kod band!")

@bot.message_handler(func=lambda msg: msg.text == "🗑 Kino o'chirish" and msg.from_user.id == ADMIN_ID)
def start_delete_kino(message):
    sent = bot.send_message(message.chat.id, "O'chirmoqchi bo'lgan kino kodini kiriting:")
    bot.register_next_step_handler(sent, delete_kino_confirm)

def delete_kino_confirm(message):
    cursor.execute("DELETE FROM kinolar WHERE kod = ?", (message.text,))
    conn.commit()
    bot.send_message(message.chat.id, f"🗑 Kod {message.text} o'chirildi.")

# --- ADMIN: KANAL AMALLARI ---
@bot.message_handler(func=lambda msg: msg.text == "📢 Kanal qo'shish" and msg.from_user.id == ADMIN_ID)
def start_add_channel(message):
    sent = bot.send_message(message.chat.id, "Kanal ID raqamini kiriting:")
    bot.register_next_step_handler(sent, add_channel_link)

def add_channel_link(message, ch_id=None):
    if ch_id is None:
        ch_id = message.text
        sent = bot.send_message(message.chat.id, "Endi kanal ssilkasini yuboring:")
        bot.register_next_step_handler(sent, add_channel_link, ch_id)
    else:
        ch_link = message.text
        try:
            cursor.execute("INSERT INTO kanallar VALUES (?, ?)", (ch_id, ch_link))
            conn.commit()
            bot.send_message(message.chat.id, f"✅ Kanal muvaffaqiyatli ulandi!")
        except sqlite3.IntegrityError:
            bot.send_message(message.chat.id, "❌ Bu kanal allaqachon qo'shilgan!")

@bot.message_handler(func=lambda msg: msg.text == "❌ Kanal o'chirish" and msg.from_user.id == ADMIN_ID)
def start_delete_channel(message):
    cursor.execute("SELECT id, link FROM kanallar")
    kanallar = cursor.fetchall()
    if not kanallar:
        bot.send_message(message.chat.id, "Bazada kanal yo'q.")
        return
    text = "O'chirmoqchi bo'lgan kanal ID raqamini yuboring:\n\n"
    for cid, clink in kanallar:
        text += f"🔹 {clink}\nID: `{cid}`\n\n"
    sent = bot.send_message(message.chat.id, text)
    bot.register_next_step_handler(sent, delete_channel_confirm)

def delete_channel_confirm(message):
    cursor.execute("DELETE FROM kanallar WHERE id = ?", (message.text,))
    conn.commit()
    bot.send_message(message.chat.id, f"❌ Kanal bazadan o'chirildi.")

# --- ADMIN: STATISTIKA VA RO'YXAT ---
@bot.message_handler(func=lambda msg: msg.text == "📊 Statistika" and msg.from_user.id == ADMIN_ID)
def statistika(message):
    cursor.execute("SELECT COUNT(*) FROM kinolar")
    kino_soni = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM kanallar")
    kanal_soni = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM foydalanuvchilar")
    user_soni = cursor.fetchone()[0]
    bot.send_message(message.chat.id, f"📊 **Baza statistikasi:**\n\n👤 Foydalanuvchilar: {user_soni} ta\n🎬 Kinolar: {kino_soni} ta\n📢 Kanallar: {kanal_soni} ta", parse_mode="Markdown")

@bot.message_handler(func=lambda msg: msg.text == "📜 Kinolar ro'yxati" and msg.from_user.id == ADMIN_ID)
def list_kinolar(message):
    cursor.execute("SELECT kod, nomi FROM kinolar LIMIT 50")
    kinolar = cursor.fetchall()
    if not kinolar:
        bot.send_message(message.chat.id, "Bazada kino yo'q.")
        return
    text = "📜 **Kinolar ro'yxati:**\n\n"
    for k in kinolar:
        text += f"🔢 Kod: {k[0]} | 🎬 Nomi: {k[1]}\n"
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

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
        caption_text = f"🎬 Nomi: {result[0]}\n🔢 Kodi: {message.text}"
        try:
            bot.send_video(message.chat.id, result[1], caption=caption_text)
        except Exception:
            bot.send_document(message.chat.id, result[1], caption=caption_text)
    else:
        bot.send_message(message.chat.id, "❌ Afsuski, bu kod bilan kino topilmadi.")

# --- ISHGA TUSHIRISH ---
if __name__ == "__main__":
    keep_alive()  # Flask serverni ishga tushiradi
    bot.infinity_polling()
