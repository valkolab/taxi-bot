import os
import telebot
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, request
from datetime import datetime

TOKEN = os.environ.get("TOKEN")
SHEET_ID = os.environ.get("SHEET_ID")
CREDS_JSON = os.environ.get("CREDS_JSON")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

def get_sheet():
    creds_dict = json.loads(CREDS_JSON)
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client.open_by_key(SHEET_ID).worksheet("Журнал дней")

user_state = {}

@bot.message_handler(commands=["start"])
def start(message):
    chat_id = message.chat.id
    user_state.pop(str(chat_id), None)
    try:
        send_menu(chat_id)
    except Exception as e:
        bot.send_message(chat_id, "Помилка: " + str(e))

def send_menu(chat_id):
    markup = telebot.types.InlineKeyboardMarkup()
    markup.row(
        telebot.types.InlineKeyboardButton("Дохід", callback_data="income"),
        telebot.types.InlineKeyboardButton("Пальне", callback_data="fuel")
    )
    markup.row(
        telebot.types.InlineKeyboardButton("Оренда авто", callback_data="rent"),
        telebot.types.InlineKeyboardButton("Витрати дня", callback_data="other")
    )
    bot.send_message(chat_id, "Вибери категорію для запису:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    names = {"income":"Дохід","fuel":"Пальне","rent":"Оренда авто","other":"Витрати дня"}
    user_state[str(chat_id)] = call.data
    bot.answer_callback_query(call.id)
    bot.send_message(chat_id, "Введи суму для " + names[call.data] + " (тільки цифри):")

@bot.message_handler(func=lambda m: str(m.chat.id) in user_state)
def handle_amount(message):
    chat_id = message.chat.id
    text = message.text.strip()
    if not text.isdigit():
        bot.send_message(chat_id, "Введи тільки цифри!")
        return
    amount = int(text)
    category = user_state.pop(str(chat_id))
    col = {"income":3,"fuel":4,"rent":5,"other":6}
    names = {"income":"Дохід","fuel":"Пальне","rent":"Оренда авто","other":"Витрати дня"}
    day = datetime.now().day
    row = 5 + day
    sheet = get_sheet()
    sheet.update_cell(row, col[category], amount)
    date_str = datetime.now().strftime("%d.%m")
    bot.send_message(chat_id, "Записано! " + date_str + " - " + names[category] + ": " + str(amount) + " грн")
    send_menu(chat_id)

@app.route("/" + TOKEN, methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/")
def index():
    return "Bot is running!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
