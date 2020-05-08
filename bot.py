import logging
import os
import datetime

import pandas as pd
import telebot

TOKEN = os.environ['TOKEN']
DEBUG = os.environ.get('DEBUG', 0)
bot = telebot.TeleBot(TOKEN)

logger = telebot.logger
telebot.logger.setLevel(logging.DEBUG)

@bot.message_handler(commands=['poker_parse_results'])
def parse_results(message):
    
    m = []
    for line in message.text.split('\n'):
        name, p = line.split(",")
        p = float(p)
        m.append((p, name))

    m.sort()
    tol = []
    while m[0][0] != 0:
        p0, name0 = m[0]
        p1, name1 = m[-1]
        
        if abs(p0) >= p1:
            print(name0, name1, p1)
            m[-1] = (0, name1)
            m[0] = (p0 + p1, name0)
        else:
            tol.append(f'{name0} скидывает {name1} {-p0}р')
            m[-1] = (p1 + p0, name1)
            m[0] = (0, name0)
        m.sort()
    
    bot.send_message(message.chat.id, '\n'.join(tol))

# @bot.message_handler(commands=['poker_start'])
# def handle_poker_start(message):
# 	bot.send_message(message.from_user.id, "Привет, чем я могу тебе помочь?")

# @bot.message_handler(commands=['poker_end'])
# def handle_poker_end(message):
# 	bot.reply_to(message, message.text)

# @bot.message_handler(commands=['poker_results'])
# def handle_poker_results(message):
# 	bot.reply_to(message, message.text)

# @bot.message_handler(commands=['poker_note'])
# def handle_poker_note(message):
# 	bot.reply_to(message, message.text)

# @bot.message_handler(commands=['poker_event'])
# def handle_poker_event(message):
# 	bot.reply_to(message, message.text)

# @bot.message_handler(commands=['poker_undo'])
# def handle_poker_undo(message):
# 	bot.reply_to(message, message.text)

# @bot.message_handler(content_types=['text'])
# def get_text_messages(message):
#     if message.text == "Привет":
#         bot.send_message(message.from_user.id, "Привет, чем я могу тебе помочь?")
#     elif message.text == "/help":
#         bot.send_message(message.from_user.id, "Напиши привет")
#     else:
#         bot.send_message(message.from_user.id, "Я тебя не понимаю. Напиши /help.")


bot.polling(none_stop=True, interval=0, timeout=20)
