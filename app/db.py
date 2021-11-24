from flask_pymongo import PyMongo


def init_db():
    mongo = PyMongo()
    return mongo


def get_db(app, mongo):
    # app.config["MONGO_URI"] = "mongodb://tms:remotetms@localhost/tms?authSource=tms"
    app.config["MONGO_URI"] = "mongodb+srv://akash:8jNYW8eVQCHORH6M@cluster0.k8zrx.mongodb.net/tms?retryWrites=true&w=majority"
    mongo.init_app(app)
