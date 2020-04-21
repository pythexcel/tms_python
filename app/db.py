import os
from flask_pymongo import PyMongo
from dotenv import load_dotenv

def init_db():
    mongo = PyMongo()
    return mongo


def get_db(app, mongo):
    APP_ROOT = os.path.join(os.path.dirname(__file__), '..')
    dotenv_path = os.path.join(APP_ROOT, '.env')
    load_dotenv(dotenv_path)
    app.config["MONGO_URI"] = os.getenv('database')
    mongo.init_app(app)
