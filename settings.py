import os


TOKEN = os.environ['TOKEN']
DEBUG = int(os.environ.get('DEBUG', 0))
PROD_MONGODB = os.environ['PROD_MONGODB']
TEST = int(os.environ.get('TEST', 0))