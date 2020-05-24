import datetime

import pymongo


class MongoDBHelper:
    def __init__(self, uri, db_name):
        self.client = pymongo.MongoClient(uri)
        self.db = self.client[db_name]

    def add_game(self, chat_id, game):
        game['chat_id'] = chat_id
        current_game = self.get_current_game(chat_id)
        if current_game is None:
            self.db.games.insert_one(game)
        else:
            raise ValueError('Существует незавершенная игра')

    def add_event_to_game(self, chat_id, event):
        current_game = self.get_current_game(chat_id)
        if current_game is not None:
            self.db.games.update_one(
                {'_id': current_game['_id']}, 
                {'$push': {'events': event}}
            )
        else:
            raise ValueError('Игра не найдена')

    def undo_event(self, chat_id):
        current_game = self.get_current_game(chat_id)
        if current_game is not None:
            last_element = current_game['events'][-1]
            self.db.games.update_one(
                {'_id': current_game['_id']}, 
                {'$pop': {'events': 1}}
            )
            return last_element
        else:
            raise ValueError('Игра не найдена')

    def end_game(self, chat_id, results, date):
        current_game = self.get_current_game(chat_id)
        if current_game is not None:
            self.db.games.update_one(
                {'_id': current_game['_id']}, 
                {'$set': {'status': 0, 'results': results, 'end': date}}
            )
        else:
            raise ValueError('Игра не найдена')

    def get_current_game(self, chat_id):
        return self.db.games.find_one({'chat_id': chat_id, 'status': 1})

    def get_all_games_in_chat(self, chat_id):
        return [game for game in self.db.games.find({'chat_id': chat_id})]

    def get_player(self, username):
        return self.db.players.find_one({'username': username})

    def get_chat_ids(self):
        chats_ids = list({game.chat_id for game in self.db.games.find()})
        return chats_ids

    def get_all_events(self, chat_id):
        current_game = self.get_current_game(chat_id)
        events = []
        if current_game is not None:
            return current_game.events
        else:
            raise ValueError('Игра не найдена')
    
    def get_start_time(self, chat_id) -> datetime.datetime:
        current_game = self.get_current_game(chat_id)
        events = []
        if current_game is not None:
            return datetime.datetime.fromisoformat(current_game.start)
        else:
            raise ValueError('Игра не найдена')

    # def add_or_update_player(self, **kwargs):
    #     coll = self.db.players
    #     result_by_id = coll.find_one({'id': int(kwargs['id'])})
    #     if result_by_id is not None:
    #         coll.update_one({'id': int(kwargs['id'])}, {'$set': kwargs})
    #     else:
    #         coll.insert_one(kwargs)
