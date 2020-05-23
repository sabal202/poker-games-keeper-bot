import datetime
import json
import logging
import os
import random
import re
import urllib

import pandas as pd
import pymongo
import telebot
from telebot import apihelper
from telebot.types import Chat, ChatMember, Dice, Message

import database
import settings
from strings import strings


def get_datetime_from_text_or_current(message) -> datetime.datetime:
    date = datetime.datetime.fromtimestamp(int(message.date))
    result_datetime = re.search(regex_datetime, message.text, re.MULTILINE)
    if result_datetime:
        date = datetime.datetime.fromisoformat(result_datetime.group(0))
    return date


def ger_player_nums_from_text(text: str) -> dict:
    matches_players = re.finditer(regex_players, text, re.MULTILINE)
    players = {}
    for match in matches_players:
        name = match.group(1)
        num = match.group(3)
        if not num:
            num = 95
        players[name] = num

    return players


def generate_message_from_transactions(transactions) -> str:
    transactions = ['{0} должен скинуть {2}р {1}'.format(
        *tr) for tr in transactions]
    return 'Кто, кому, сколько должен скинуть:\n' + '\n'.join(transactions)

regex_datetime = r"(([12]\d{3})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01]) ([01]\d}|2[0-3])(:([0-5]\d)){1,2})"
regex_players = r"(@\w+)([\s,:;|\\/]+|$)([-+]?\d+|)"

bot = telebot.TeleBot(settings.TOKEN)

db_helper = database.MongoDBHelper(settings.PROD_MONGODB, 'db')

logger = telebot.logger
telebot.logger.setLevel(logging.DEBUG)

apihelper.ENABLE_MIDDLEWARE = True


@bot.middleware_handler(update_types=['message'])
def fix_message(bot_instance, message):
    bot_instance.is_from_chat = message.from_user.id != message.chat.id
    if bot_instance.is_from_chat:
        chat_administrators = bot.get_chat_administrators(message.chat.id)
        admin_ids = [admin.user.id for admin in chat_administrators]
        bot_instance.is_from_admin = message.from_user.id in admin_ids
    else:
        bot_instance.is_from_admin = False

    if message.content_type == 'text' and message.text.startswith('/poker'):
        if bot.is_from_chat and not bot.is_from_admin:
            bot.reply_to(message, strings['not_admin'])
            return
        elif not bot.is_from_chat:  # TODO изменить поведение
            bot.reply_to(message, strings['not_in_chat'])
            return

def parse_results(message):
    lines = message.text.split('\n')[1:]

    if not lines:
        bot.reply_to(message, strings['error_noresults'])
        return

    m = []
    for i, line in enumerate(lines, 1):
        try:
            splitter = line.rfind(' ')
            name, p = line[:splitter], line[splitter + 1:]
            p = int(p)  # TODO может быть использовать дробные
            m.append((p, name))
        except Exception as err:
            bot.reply_to(message, strings['error_ith_line'].format(i))
            return

    sum_of_results = sum([i[0] for i in m])

    if sum_of_results != 0:
        bot.reply_to(message, strings['error_sum_of_results'].format(sum_of_results))
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
    bot.send_message(message.from_user.id, strings['info'])


@bot.message_handler(commands=['send_nudes'])
def handle_poker_start(message):
    with open('photos.txt', mode='r', encoding='utf8') as file:
        urls = [i.replace('\n', '') for i in file.readlines()]

    url = random.choice(urls)
    f = open('out.jpg', 'wb')
    f.write(urllib.request.urlopen(url).read())
    f.close()
    img = open('out.jpg', 'rb')
    bot.send_photo(message.chat.id, img)


@bot.message_handler(commands=['poker_start'])
def handle_poker_start(message):
    date = get_datetime_from_text_or_current(message)
    players = ger_player_nums_from_text(message.text)

    bot.reply_to(message, json.dumps(players, indent=4))

    # TODO: DB


@bot.message_handler(commands=['poker_end'])
def handle_poker_end(message):
    date = get_datetime_from_text_or_current(message)
    players = ger_player_nums_from_text(message.text)

    bot.reply_to(message, json.dumps(players, indent=4))

    # TODO: DB


@bot.message_handler(commands=['poker_results'])
def handle_poker_results(message):
    if bot.is_from_chat and not bot.is_from_admin:
        bot.reply_to(message, strings['not_admin'])
        return
    elif not bot.is_from_chat:  # TODO изменить поведение
        bot.reply_to(message, strings['not_in_chat'])
        return

    parse_results(message.text)


@bot.message_handler(commands=['poker_in'])
def handle_poker_event(message):
    # TODO: DB
    pass


@bot.message_handler(commands=['poker_out'])
def handle_poker_event(message):
    # TODO: DB
    pass


@bot.message_handler(commands=['poker_add', 'poker_minus'])
def handle_poker_event(message):
    # TODO: DB
    pass

@bot.message_handler(commands=['poker_undo'])
def handle_poker_undo(message):
    # bot.reply_to(message, message.text)
    pass


@bot.message_handler(content_types=['dice'])
def handle_poker_undo(message):
    bot.reply_to(message, 'Gotted')
    bot.reply_to(message, f'Gotted {message.dice.value}')

bot.polling(none_stop=True, interval=0, timeout=20)
