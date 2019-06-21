from app import mongo
from bson.objectid import ObjectId
import requests
from app.config import webhook_url, slack_token
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

#Function for find webhook_url
def load_hook():
    url = mongo.db.slack_tokens.find_one({
        "webhook_url": {"$exists": True}
    }, {"webhook_url": 1, '_id': 0})
    web_url = url['webhook_url']
    return web_url
#function for send mesg 
def slack_message(msg):
    slackmsg = {"text": msg}
    webhook_url = load_hook()
    response = requests.post(
        webhook_url, json=slackmsg,
        headers={'Content-Type': 'application/json'})
#function for find slack_token
def load_token():
    token = mongo.db.slack_tokens.find_one({
        "slack_token": {"$exists": True}
    }, {"slack_token": 1, '_id': 0})
    sl_token = token['slack_token']
    return sl_token

def slack_msg(channel, msg):
    print(channel)
    sc = SlackClient(slack_token)
    for data in channel:
        sc.api_call(
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

#function for find monthly_manager_reminder mesg from db
def load_monthly_manager_reminder():
    msg = mongo.db.schdulers_msg.find_one({
        "monthly_manager_reminder": {"$exists": True}
    }, {"monthly_manager_reminder": 1, '_id': 0})
    manager_reminder = msg['monthly_manager_reminder']
    return manager_reminder

#function for find monthly_reminder mesg from db
def monthly_remainder():
    msg = mongo.db.schdulers_msg.find_one({
        "monthly_remainder": {"$exists": True}
    }, {"monthly_remainder": 1, '_id': 0})
    monthly_remainder = msg['monthly_remainder']
    return monthly_remainder

def monthly_remainder():
    msg = mongo.db.schdulers_msg.find_one({
        "missed_checkin": {"$exists": True}
    }, {"missed_checkin": 1, '_id': 0})
    missed_checkin = msg['missed_checkin']
    return missed_checkin


#function for find review_activity mesg from db
def load_review_activity():
    msg = mongo.db.schdulers_msg.find_one({
        "review_activity": {"$exists": True}
    }, {"review_activity": 1, '_id': 0})
    review_msg = msg['review_activity']
    return review_msg

#function for find first two days weekly remienderr mesg
def load_weekly1():
    msg = mongo.db.schdulers_msg.find_one({
        "weekly_remainder1": {"$exists": True}
    }, {"weekly_remainder1": 1, '_id': 0})
    weekly_msg = msg['weekly_remainder1']
    return weekly_msg

#function for find first two days weekly remienderr mesg
def load_weekly2():
    msg = mongo.db.schdulers_msg.find_one({
        "weekly_remainder2": {"$exists": True}
    }, {"weekly_remainder2": 1, '_id': 0})
    weekly_msg2 = msg['weekly_remainder2']
    return weekly_msg2



