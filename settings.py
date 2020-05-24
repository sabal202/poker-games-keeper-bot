import os


TOKEN = os.environ.get('TOKEN', '')
DEBUG = int(os.environ.get('DEBUG', 0))
PROD_MONGODB = os.environ.get('PROD_MONGODB', '')
TEST = int(os.environ.get('TEST', 1))
DEBUG_CHAT_ID = int(os.environ.get('DEBUG_CHAT_ID', -1001240178139))