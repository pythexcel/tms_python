from app import mongo
from bson.objectid import ObjectId
import requests
from slackclient import SlackClient


def serialize_doc(doc):
    doc["_id"] = str(doc["_id"])
    return doc


def get_manager_profile(manager):

    ret = mongo.db.users.find_one({
        "_id": ObjectId(manager["_id"]),
        "status": "Enabled"
    })
    # del ret["_id"]
    if "managers" in ret:
        del ret["managers"]
    if "password" in ret:
        del ret["password"]
    if "username" in ret:
        del ret["username"]
    if "kpi_id" in ret:
        del ret["kpi_id"]
    ret['_id'] = str(ret['_id'])
    if "weight" in ret:
        ret["weight"] = manager["weight"]
    return ret

def load_hook():
    url = mongo.db.slack_tokens.find_one({
        "webhook_url": {"$exists": True}
    }, {"webhook_url": 1, '_id': 0})
    web_url = url['webhook_url']
    return web_url


def slack_message(msg):
    slackmsg = {"text": msg}
    webhook_url = load_hook()
    response = requests.post(
        webhook_url, json=slackmsg,
        headers={'Content-Type': 'application/json'})


def load_token():
    token = mongo.db.slack_tokens.find_one({
        "slack_token": {"$exists": True}
    }, {"slack_token": 1, '_id': 0})
    sl_token = token['slack_token']
    return sl_token


def slack_msg(channel, msg):
    token = load_token()
    sc = SlackClient(token)
    for data in channel:
        sendMsgToSlack = sc.api_call(
            "chat.postMessage",
            channel=data,
            text=msg
        )


# function for getting all the juniors of managers
def get_manager_juniors(id):
    users = mongo.db.users.find({
        "managers": {
            "$elemMatch": {"_id": str(id)}
        }
    })
    user_ids = []
    for user in users:
        user_ids.append(str(user['_id']))
    return user_ids        
