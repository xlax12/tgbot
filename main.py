import os
import random
import sqlite3
from telebot import TeleBot, types

# Конфигурация
TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = 1873225352
bot = TeleBot(TOKEN)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('furry_rng.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (user_id INTEGER PRIMARY KEY, username TEXT, score INTEGER DEFAULT 0, boost REAL DEFAULT 1.0)''')
    conn.commit()
    conn.close()

init_db()

# --- Вспомогательные функции ---
def get_user_data(user_id, username):
    conn = sqlite3.connect('furry_rng.db')
    cursor = conn.cursor()
    cursor.execute("SELECT score, boost FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if not result:
        cursor.execute("INSERT INTO users (user_id, username, score) VALUES (?, ?, ?)", (user_id, username, 0))
        conn.commit()
        return 0, 1.0
    return result

def update_score(user_id, new_score):
    conn = sqlite3.connect('furry_rng.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET score = ? WHERE user_id = ?", (new_score, user_id))
    conn.commit()
    conn.close()

# --- Главное меню ---
def main_menu(user_id):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🍀 Проверить удачу", callback_data="roll"),
        types.InlineKeyboardButton("🏆 Лидерборд", callback_data="leaderboard"),
        types.InlineKeyboardButton("👤 Профиль", callback_data="profile")
    )
    if user_id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("⚙️ Админ панель", callback_data="admin_panel"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    get_user_data(message.from_user.id, message.from_user.first_name)
    text = (f"Привет! ✨ Это бот фурри рнг, где ты можешь проверить свою удачу и узнать насколько ты везучий) 🐾\n\n"
            f"В данном боте есть топ, где ты можешь узнать на каком ты месте ~ Удачной игры, друг мой! 🦊")
    bot.send_message(message.chat.id, text, reply_markup=main_menu(message.from_user.id))

# --- Обработка кнопок ---
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    user_id = call.from_user.id
    score, boost = get_user_data(user_id, call.from_user.first_name)

    if call.data == "roll":
        # Логика RNG: чем больше число, тем меньше шанс
        # Используем экспоненциальное распределение для имитации редкости
        num = int(random.expovariate(1/100000) * boost)
        if num > 1000000000: num = 1000000000
        if num < 1: num = 1
        
        update_score(user_id, score + num)
        
        if num < 100000:
            comment = "🐾 Это нормальный показатель, лапками шевелим!"
        elif num < 1000000:
            comment = "🌟 Ого, неплохо! Ты довольно милый везунчик!"
        else:
            comment = f"🔥 **АФИГЕННЫЙ ПОКАЗАТЕЛЬ! ТЫ ЛЕГЕНДАРНЫЙ ФУРРИ!** 🐾"

        text = f"Ого, твой фурри метр показывает:\n💎 **{num:,}**\n\n{comment}\n\nТвоя стата обновлена на это число! ✨"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 Проверить снова", callback_data="roll"))
        markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="to_main"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "leaderboard":
        conn = sqlite3.connect('furry_rng.db')
        cursor = conn.cursor()
        cursor.execute("SELECT username, score FROM users ORDER BY score DESC LIMIT 30")
        rows = cursor.fetchall()
        conn.close()
        
        leader_text = "🏆 **Вот таблица фурри лидеров ~**\n\n"
        for i, row in enumerate(rows, 1):
            leader_text += f"{i}. {row[0]} — 🐾 {row[1]:,}\n"
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="to_main"))
        bot.edit_message_text(leader_text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "profile":
        text = f"Привет, {call.from_user.first_name}! 👋\n\nМой фурри метр показал такое число:\n🐾 **{score:,}**\n\nЯ считаю это неплохой показатель! ✨"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="to_main"))
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif call.data == "to_main":
        text = "Главное меню 🐾"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=main_menu(user_id))

    # --- Админ панель ---
    elif call.data == "admin_panel" and user_id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("💰 Выдача очков", callback_data="admin_give"),
            types.InlineKeyboardButton("📢 Объявление", callback_data="admin_broadcast"),
            types.InlineKeyboardButton("📈 Подкрутка шансов", callback_data="admin_boost"),
            types.InlineKeyboardButton("⬅️ Назад", callback_data="to_main")
        )
        bot.edit_message_text("Здарова админчик, твои полномочия: 👑", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data == "admin_give":
        msg = bot.send_message(call.message.chat.id, "Ну чтож, кому выдадим дофига фурри очков? Пиши ID пользователя (цифрами):")
        bot.register_next_step_handler(msg, process_give_id)

    elif call.data == "admin_broadcast":
        msg = bot.send_message(call.message.chat.id, "Что рассылаем? Пиши текст:")
        bot.register_next_step_handler(msg, process_broadcast)

    elif call.data == "admin_boost":
        msg = bot.send_message(call.message.chat.id, "Так так так, кому подкручиваем? Пиши ID пользователя:")
        bot.register_next_step_handler(msg, process_boost_id)

# --- Админские шаги ---
def process_give_id(message):
    try:
        target_id = int(message.text)
        msg = bot.send_message(message.chat.id, "Услышал, сколько выдадим? Пиши:")
        bot.register_next_step_handler(msg, lambda m: process_give_amount(m, target_id))
    except: bot.send_message(message.chat.id, "Ошибка! Нужен числовой ID.")

def process_give_amount(message, target_id):
    try:
        amount = int(message.text)
        conn = sqlite3.connect('furry_rng.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET score = score + ? WHERE user_id = ?", (amount, target_id))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, "Успешно выдал! ✅")
        bot.send_message(target_id, f"Ого! Админ тебе выдал {amount:,} очков! ✨🐾")
    except: bot.send_message(message.chat.id, "Ошибка ввода!")

def process_broadcast(message):
    conn = sqlite3.connect('furry_rng.db')
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()
    
    success = 0
    fail = 0
    for user in users:
        try:
            bot.send_message(user[0], message.text)
            success += 1
        except: fail += 1
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="admin_panel"))
    bot.send_message(message.chat.id, f"📢 Рассылка завершена!\n✅ Успешно: {success}\n❌ Ошибок: {fail}", reply_markup=markup)

def process_boost_id(message):
    try:
        target_id = int(message.text)
        msg = bot.send_message(message.chat.id, "Введи проценты, на сколько увеличить шанс (например, 50%):")
        bot.register_next_step_handler(msg, lambda m: process_boost_value(m, target_id))
    except: bot.send_message(message.chat.id, "Ошибка ID.")

def process_boost_value(message, target_id):
    if '%' in message.text:
        try:
            percent = float(message.text.replace('%', ''))
            multiplier = 1 + (percent / 100)
            conn = sqlite3.connect('furry_rng.db')
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET boost = ? WHERE user_id = ?", (multiplier, target_id))
            conn.commit()
            conn.close()
            bot.send_message(message.chat.id, "Подкрутил! 🎡")
            bot.send_message(target_id, f"Ого, админ подкрутил тебе шансы на {percent}%! 🍀🐾")
        except: bot.send_message(message.chat.id, "Ошибка в процентах.")
    else:
        bot.send_message(message.chat.id, "Забыл знак %!")

if __name__ == "__main__":
    bot.infinity_polling()
