import telebot
import logging
import os

TOKEN = os.environ['TOKEN']
bot = telebot.TeleBot(TOKEN)

logger = telebot.logger
telebot.logger.setLevel(logging.DEBUG)


@bot.message_handler(commands=['poker_start'])
def handle_poker_start(message):
	bot.reply_to(message, message.text)

@bot.message_handler(commands=['poker_end'])
def handle_poker_end(message):
	bot.reply_to(message, message.text)

@bot.message_handler(commands=['poker_results'])
def handle_poker_results(message):
	bot.reply_to(message, message.text)

@bot.message_handler(commands=['poker_note'])
def handle_poker_note(message):
	bot.reply_to(message, message.text)

@bot.message_handler(commands=['poker_event'])
def handle_poker_event(message):
	bot.reply_to(message, message.text)

@bot.message_handler(commands=['poker_undo'])
def handle_poker_undo(message):
	bot.reply_to(message, message.text)

@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    if message.text == "Привет":
        bot.send_message(message.from_user.id, "Привет, чем я могу тебе помочь?")
    elif message.text == "/help":
        bot.send_message(message.from_user.id, "Напиши привет")
    else:
        bot.send_message(message.from_user.id, "Я тебя не понимаю. Напиши /help.")


bot.polling(none_stop=True, interval=0, timeout=20)
