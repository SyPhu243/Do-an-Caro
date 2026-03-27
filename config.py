import os
from dotenv import load_dotenv
load_dotenv()


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY','dev-secret')
    DB_HOST = os.getenv('DB_HOST','localhost')
    DB_USER = os.getenv('DB_USER','phu')
    DB_PASS = os.getenv('DB_PASS','2403200203')
    DB_NAME = os.getenv('DB_NAME','caro_db')