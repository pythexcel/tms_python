from flask_pymongo import PyMongo


def init_db():
    mongo = PyMongo()
    return mongo


def get_db(app, mongo):
    app.config["MONGO_URI"] = "mongodb://localhost:27017/test_db_manish"
    mongo.init_app(app)
