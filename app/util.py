from app import mongo
from bson.objectid import ObjectId
from app.config import slack_url,web_url
import requests


def serialize_doc(doc):
    doc["_id"] = str(doc["_id"])
    return doc

def slack_msg(msg):
    webhook_url = slack_url
    webhook_pvt = web_url

    slack_data = {'text': msg }

    response = requests.post(
        webhook_url, json=slack_data,
        headers={'Content-Type': 'application/json'}
    )
    response_pvt = requests.post(
        webhook_pvt, json=slack_data,
        headers={'Content-Type': 'application/json'}
    )
    if response_pvt.status_code != 200:
        raise ValueError(
            'Request to slack returned an error %s, the response is:\n%s'
            % (response.status_code, response.text)
        )
    if response.status_code != 200:
        raise ValueError(
            'Request to slack returned an error %s, the response is:\n%s'
            % (response.status_code, response.text)
        )

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

