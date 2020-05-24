import datetime
import json
import logging
import os
import random
import re
import urllib
from typing import Dict, List, Set

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pymongo
import telebot
from dateutil.relativedelta import relativedelta
from telebot import apihelper
from telebot.types import Chat, ChatMember, Dice, Message

import database
import settings
from strings import strings


class STATES:
    IDLE = 0
    INGAME = 1


class DEFAULTS:
    NUM_ON_START = 95
    NUM_ON_IN = 95
    NUM_ON_ADD = 95
    NUM_ON_MINUS = 95
    NUM_ON_OUT = 0
    NUM_ON_END = 0


def get_datetime_from_text_or_current(message: Message) -> datetime.datetime:
    date = datetime.datetime.fromtimestamp(int(message.date))
    
    try:
        date = datetime.datetime.fromtimestamp(int(message.forward_date))
    except Exception:
        pass

    result_datetime = re.search(regex_datetime, message.text, re.MULTILINE)
    if result_datetime:
        date = datetime.datetime.fromisoformat(result_datetime.group(0))
    return date


def ger_player_nums_from_text(text: str, default_num: int) -> Dict[str, int]:
    matches_players = re.finditer(regex_players, text, re.MULTILINE)
    players = {}
    for match in matches_players:
        name = match.group(1)
        num = match.group(2)
        if not num:
            num = default_num
        else:
            num = int(num)
        players[name] = num
    return players


regex_datetime = r"(([12]\d{3})-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01]) ([01]\d}|2[0-3])(:([0-5]\d)){1,2})"
regex_players = r"(?<=\W)(@\w+)[\s,:;]+([-+]?\d+|)"
regex_chat_id = r"^\/[\w@]+\s+(-?\d+)[\s\$]"
datetimeformat = '%Y-%m-%d %H:%M:%S' 
timeformat = '%H:%M:%S' 
dateformat = '%Y-%m-%d'

bot = telebot.TeleBot(settings.TOKEN)

db_helper = database.MongoDBHelper(settings.PROD_MONGODB, 'db')

logger = telebot.logger
telebot.logger.setLevel(logging.DEBUG)

apihelper.ENABLE_MIDDLEWARE = True


@bot.middleware_handler(update_types=['message'])
def fix_message(bot_instance, message: Message):
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

        chat_id = message.chat.id
        result_chat_id = re.search(regex_chat_id, message.text, re.MULTILINE)
        if result_chat_id:
            chat_id = int(regex_chat_id.group(1))

        if settings.DEBUG:
            chat_id = settings.DEBUG_CHAT_ID

        message.chat_id = chat_id


def parse_results(results: Dict[str, int]) -> List[str]:
    if not results:
        return [strings['error_noresults']]

    m = []
    for name, num in results.items():
        m.append((num, name))

    sum_of_results = sum([i[0] for i in m])

    if sum_of_results != 0:
        return [strings['error_sum_of_results'].format(sum_of_results)]

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
    generated_lines = [
        strings['transactions_body'].format(*tr)
        for tr in transactions
    ]
    return [strings['transactions_title']] + generated_lines


@bot.message_handler(commands=['info'])
def handle_info(message: Message):
    bot.send_message(message.from_user.id, strings['info'])


@bot.message_handler(commands=['send_nudes'])
def handle_send_nudes(message: Message):
    with open('photos.txt', mode='r', encoding='utf8') as file:
        urls = [i.replace('\n', '') for i in file.readlines()]

    url = random.choice(urls)
    f = open('out.jpg', 'wb')
    f.write(urllib.request.urlopen(url).read())
    f.close()
    img = open('out.jpg', 'rb')
    bot.send_photo(message.chat.id, img)


@bot.message_handler(commands=['status'])
def handle_status(message: Message):
    pass


@bot.message_handler(commands=['poker_start'])
def handle_poker_start(message: Message):
    date = get_datetime_from_text_or_current(message)
    players = ger_player_nums_from_text(message.text, DEFAULTS.NUM_ON_START)
    
    game = dict(
        name=date.strftime(dateformat),
        type='cash',
        status=STATES.INGAME,
        start=date.strftime(datetimeformat),
        end='',
        events=[],
        results=[]
    )
    try:
        db_helper.add_game(message.chat_id, game)
        for player, num in players.items():
            event = dict(
                date=date,
                username=player,
                type='in',
                num=num
            )
            db_helper.add_event_to_game(message.chat_id, event)
    except ValueError as err:
        bot.send_message(message.chat.id, 'Существует незавершенная игра')


@bot.message_handler(commands=['poker_end'])
def handle_poker_end(message: Message):
    date = get_datetime_from_text_or_current(message)
    players = ger_player_nums_from_text(message.text, DEFAULTS.NUM_ON_END)

    events = db_helper.get_all_events(message.chat_id)

    players_in_game = set()
    cash_in_game = 0
    player_cash_status_in_game = {}
    player_cash_delta = {}
    for event in events:
        username = event['username']
        if username not in player_cash_status_in_game:
            player_cash_status_in_game[username] = 0
            player_cash_delta[username] = 0

        type_ = event['type']
        num = event['num']
        # TODO: check for errors in events
        if type_ == 'in':
            player_cash_status_in_game[username] += num
            player_cash_delta[username] -= num
            cash_in_game += num
            players_in_game.add(username)
        elif type_ == 'add':
            player_cash_status_in_game[username] += num
            player_cash_delta[username] -= num
            cash_in_game += num
        elif type_ == 'minus':
            player_cash_status_in_game[username] -= num
            player_cash_delta[username] += num
            cash_in_game -= num
        elif type_ == 'out':
            player_cash_status_in_game[username] = num
            player_cash_delta[username] += num
            cash_in_game -= num
            players_in_game.difference_update({username})

    errors = []
    for player in players:
        if player not in player_cash_status_in_game or player not in players_in_game:
            errors.append(strings['player_not_in_game'].format(player))
    bot.send_message(message.from_user.id, json.dumps(player_cash_status_in_game, indent=4))
    bot.send_message(message.from_user.id, json.dumps(players, indent=4))
    bot.send_message(message.from_user.id, str(players_in_game))

    players_lasts_in_game = players_in_game.difference(set(players.keys()))
    if players_lasts_in_game:
        errors.append(strings['not_enough_players_out'].format(', '.join(players_lasts_in_game)))
        

    cash_in_game_with_end = cash_in_game
    player_cash_status_with_end = player_cash_status_in_game.copy()
    player_cash_delta_with_end = player_cash_delta.copy()
    for player, num in players.items():
        player_cash_status_with_end[player] = num
        player_cash_delta_with_end[player] += num
        cash_in_game_with_end -= num


    sum_cash_results = sum(player_cash_delta.values())
    if sum_cash_results != 0:
        errors.append(strings['error_sum_of_results'].format(sum_cash_results))

    if errors:
        errors.insert(0, strings['got_errors_title'])
        errors.append(strings['got_errors_footer'])
        errors.append('')
        errors.append(strings['pre_results'])

        for player, delta in player_cash_delta.items():
            errors.append(strings['result_body'].format(player, delta))

        errors.append('')
        errors.append(strings['pre_results_with_end'])
        for player, delta in player_cash_delta_with_end.items():
            errors.append(strings['result_body'].format(player, delta))

        reply = '\n'.join(errors)
        bot.send_message(message.chat.id, reply)
        return

    # if all ok
    for player, num in players.items():
        event = dict(
            date=date,
            username=player,
            type='out',
            num=num
        )
        db_helper.add_event_to_game(message.chat_id, event)
    
    start_date = db_helper.get_start_time(message.chat_id)

    db_helper.end_game(message.chat_id, results=player_cash_delta_with_end, date=date)

    r_d = relativedelta(date, start_date)
    if r_d.days % 10 == 1:
        days = f'{r_d.days} сутки'
    else:
        days = f'{r_d.days} суток'
    timedelta = strings['timedelta'].format(days=days, hours=r_d.hours, minutes=r_d.minutes)

    lines = [
        strings['endgame_title'].format(
            date=start_date.strftime(dateformat), 
            timedelta=timedelta, 
            start_time=start_date.strftime(timeformat),
            end_time=date.strftime(timeformat)),
        strings['endgame_podtitle'].format(
            n_players=len(player_cash_delta_with_end)
        ),
        strings['endgame_footer']
    ]

    bot.send_message(message.chat.id, '\n'.join(lines))

    lines_transactions = parse_results(player_cash_delta_with_end)
    bot.send_message(message.chat.id, '\n'.join(lines_transactions))

@bot.message_handler(commands=['poker_parse_results'])
def handle_poker_parse_results(message: Message):
    results = ger_player_nums_from_text(message.text, DEFAULTS.NUM_ON_END)
    lines = parse_results(results)
    reply = '\n'.join(lines)
    bot.reply_to(message, reply)


@bot.message_handler(commands=['poker_add', 'poker_minus', 'poker_out', 'poker_in'])
def handle_poker_event(message: Message):
    date = get_datetime_from_text_or_current(message)
    type_ = message.text.split()[0].split('@')[0][7:]
    default_num_from_type = {
        'add': DEFAULTS.NUM_ON_ADD, 
        'minus': DEFAULTS.NUM_ON_MINUS, 
        'out': DEFAULTS.NUM_ON_OUT, 
        'in': DEFAULTS.NUM_ON_IN
    }
    players = ger_player_nums_from_text(message.text, default_num_from_type[type_])

    wrote = [strings['wrote_to_db']]
    
    for player, num in players.items():
        wrote.append(f'{player} {type_} {num}')
        event = dict(
            date=date,
            username=player,
            type=type_,
            num=num
        )
        db_helper.add_event_to_game(message.chat_id, event)

    reply = '\n'.join(wrote)
    bot.send_message(message.from_user.id, reply)


@bot.message_handler(commands=['poker_undo'])
def handle_poker_undo(message: Message):
    event = db_helper.undo_event(message.chat_id)
    bot.send_message(message.from_user.id, json.dumps(event, indent=4))


@bot.message_handler(commands=['poker_clear_events'])
def handle_poker_clear_events(message: Message):
    db_helper.poker_clear_events(message.chat_id)
    bot.send_message(message.from_user.id, strings['cleared_events'])


@bot.message_handler(commands=['poker_delete_current_game'])
def handle_poker_delete_current_game(message: Message):
    db_helper.delete_game(message.chat_id)
    bot.send_message(message.from_user.id, strings['deleted_game'])


@bot.message_handler(commands=['poker_plot'])
def handle_poker_plot(message: Message):
    pass


@bot.message_handler(content_types=['dice'])
def handle_dice(message: Message):
    if message.dice.value == 6:
        bot.send_message(message.chat.id, strings['you_are_lucky'])

bot.polling(none_stop=True, interval=0, timeout=20)
