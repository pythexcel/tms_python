from app import mongo
from bson.objectid import ObjectId
import requests
from app.config import webhook_url


def serialize_doc(doc):
    doc["_id"] = str(doc["_id"])
    return doc


def get_manager_profile(manager):

    ret = mongo.db.users.find_one({
        "_id": ObjectId(manager["_id"])
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

def slack_message(msg):
    slackmsg = {"text": msg}
    response = requests.post(
    webhook_url, json=slackmsg,
    headers={'Content-Type': 'application/json'})

def slack_msg(channel,msg):
   print(channel)
   sc = SlackClient(slack_token)
   for data in channel:
       sc.api_call(
           "chat.postMessage",
           channel=data,
           text=msg
       )
