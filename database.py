import pymongo


class MongoDBHelper:
    def __init__(self, uri, db_name):
        self.client = pymongo.MongoClient(uri)
        self.db = self.client[db_name]

    def add_or_update_player(self, **kwargs):
        coll = self.db.players
        result_by_id = coll.find_one({'id': int(kwargs['id'])})

        if result_by_id is not None:
            coll.update_one({'id': int(kwargs['id'])}, {'$set': kwargs})
        else:
            coll.insert_one(kwargs)

    # def add_game(self, chat_id, player_ids, )

    def get_player(self, username):
        return self.db.players.find_one({'username': username})
    
    def get_chat_ids(self):
        all_chats_collections_names = [chat.name for chat in self.db.list_collections(filter={'name': {"$regex": 'chats*'}})]
        chats_ids = [int(name.split('.')[1]) for name in all_chats_collections_names]
        return chats_ids
    
    def get_all_games_in_chat(self, chat_id):
        return [game for game in self.db.chats[str(chat_id)].find({})]
