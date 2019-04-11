from flask_pymongo import PyMongo


def init_db():
    mongo = PyMongo()
    return mongo


def get_db(app, mongo):
    app.config["MONGO_URI"] = "mongodb+srv://xmage:xmage@cluster0-xooqb.mongodb.net/test?retryWrites=true"
    mongo.init_app(app)
