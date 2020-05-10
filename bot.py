import datetime
import logging
import os

import pandas as pd
import pymongo
import telebot
from telebot import apihelper

import settings
import database


def fix_text_escaping(text):
    return text.encode().decode('unicode_escape')

def generate_message_from_transactions(transactions):
    transactions = ['{0} должен скинуть {2}р {1}'.format(*tr) for tr in transactions]
    return 'Кто, кому, сколько должен скинуть:\n' + '\n'.join(transactions)

bot = telebot.TeleBot(settings.TOKEN)
db_helper = database.MongoDBHelper(settings.PROD_MONGODB)

logger = telebot.logger
telebot.logger.setLevel(logging.DEBUG)

apihelper.ENABLE_MIDDLEWARE = True

@bot.middleware_handler(update_types=['message'])
def fix_message(bot_instance, message):
    bot_instance.fixed_text = fix_text_escaping(message.text)
    
    bot_instance.is_from_chat = message.from_user.id != message.chat.id
    if bot_instance.is_from_chat:
        admins = [admin.user.id for admin in bot.get_chat_administrators(message.chat.id)]
        bot_instance.is_from_admin = message.from_user.id in admins
    else:
        bot_instance.is_from_admin = False 

@bot.message_handler(commands=['poker_parse_results'])
def parse_results(message):
    if bot.is_from_chat and not bot.is_from_admin:
        bot.reply_to(message, 'Вы не администратор, поэтому вы не можете использовать эту функцию')
        return
    elif not bot.is_from_chat: # TODO изменить поведение
        bot.reply_to(message, 'Сообщение отправлено не в чате, поэтому вы не можете использовать эту функцию')
        return

    lines = bot.fixed_text.split('\n')[1:]

    if not lines:
        bot.reply_to(message, 'Вы не написали результатов')
        return

    m = []
    for i, line in enumerate(lines, 1):
        try:
            splitter = line.rfind(' ')
            name, p = line[:splitter], line[splitter + 1:]
            p = int(p) # TODO может быть использовать дробные
            m.append((p, name))
        except Exception as err:
            bot.reply_to(message, f'Ошибка в {i} строчке результатов')
            return

    sum_of_results = sum([i[0] for i in m])

    if sum_of_results != 0:
        bot.reply_to(message, f'Ошибка, сумма результатов равна {sum_of_results}, а не 0')
        return

    m.sort()
    transactions = []
    while m[0][0] != 0:
        p0, name0 = m[0]
        p1, name1 = m[-1]
        
        if abs(p0) >= p1:
            transactions.append((name0, name1, p1))
            m[-1] = (0, name1)
            m[0] = (p0 + p1, name0)
        else:
            transactions.append((name0, name1, -p0))
            m[-1] = (p1 + p0, name1)
            m[0] = (0, name0)
        m.sort()

    transactions.sort()

    reply = generate_message_from_transactions(transactions)
    bot.reply_to(message, reply)

@bot.message_handler(commands=['info'])
def handle_poker_start(message):
	bot.send_message(message.chat.id, "Я существую, чтобы упростить отслеживание результатов игр в покер")

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
