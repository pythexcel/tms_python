from app import mongo
from bson.objectid import ObjectId
import requests
#from slackclient import SlackClient


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

def secret_key():
    msg = mongo.db.slack_tokens.find_one({
        "secret_key": {"$exists": True}
    }, {"secret_key": 1, '_id': 0})
    secret_key = msg['secret_key']
    return secret_key


# function for getting all the juniors of managers
def get_manager_juniors(id):
    users = mongo.db.users.find({
        "status":"Enabled",
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
    if msg is not None:
        manager_reminder = msg['monthly_manager_reminder']
        return manager_reminder
    else:
        reminder=default['monthly_manager_reminder']
        return reminder

def load_weekly_notes():
    msg = mongo.db.schdulers_msg.find_one({
        "weekly_report_notes": {"$exists": True}
    }, {"weekly_report_notes": 1, '_id': 0})
    if msg is not None:
        manager_reminder = msg['weekly_report_notes']
        return manager_reminder
    else:
        reminder=default['weekly_report_notes']
        return reminder
    
        
#function for find monthly_reminder mesg from db
def load_monthly_remainder():
    msg = mongo.db.schdulers_msg.find_one({
        "monthly_remainder": {"$exists": True}
    }, {"monthly_remainder": 1, '_id': 0})
    if msg is not None:    
        load_monthly_remainder = msg['monthly_remainder']
        return load_monthly_remainder
    else:
        monthly_remainder=default['monthly_remainder']
        return monthly_remainder


def load_missed_review():
    msg = mongo.db.schdulers_msg.find_one({
        "missed_reviewed_mesg": {"$exists": True}
    }, {"missed_reviewed_mesg": 1, '_id': 0})
    if msg is not None:
        manager_reminder = msg['missed_reviewed_mesg']
        return manager_reminder
    else:
        reminder=default['missed_reviewed_mesg']
        return reminder


def missed_checkin():
    msg = mongo.db.schdulers_msg.find_one({
        "missed_checkin": {"$exists": True}
    }, {"missed_checkin": 1, '_id': 0})
    if msg is not None:
        missed_checkin = msg['missed_checkin']
        return missed_checkin
    else:
        checkin=default['missed_checkin']
        return checkin

def load_monthly_report_mesg():
    msg = mongo.db.schdulers_msg.find_one({
        "monthly_report_mesg": {"$exists": True}
    }, {"monthly_report_mesg": 1, '_id': 0})
    if msg is not None:
        review_msg = msg['monthly_report_mesg']
        return review_msg
    else:
        rev_msg=default["monthly_report_mesg"]
        return rev_msg


def load_weekly_report_mesg():
    msg = mongo.db.schdulers_msg.find_one({
        "weekly_report_mesg": {"$exists": True}
    }, {"weekly_report_mesg": 1, '_id': 0})
    if msg is not None:
        review_msg = msg['weekly_report_mesg']
        return review_msg
    else:
        rev_msg=default["weekly_report_mesg"]
        return rev_msg



#function for find review_activity mesg from db
def load_review_activity():
    msg = mongo.db.schdulers_msg.find_one({
        "review_activity": {"$exists": True}
    }, {"review_activity": 1, '_id': 0})
    if msg is not None:
        review_msg = msg['review_activity']
        return review_msg
    else:
        rev_msg=default["review_activity"]
        return rev_msg

#function for find first two days weekly remienderr mesg
def load_weekly1():
    msg = mongo.db.schdulers_msg.find_one({
        "weekly_remainder1": {"$exists": True}
    }, {"weekly_remainder1": 1, '_id': 0})
    if msg is not None:
        weekly_msg = msg['weekly_remainder1']
        return weekly_msg
    else:
        week_mesg=default["weekly_remainder1"]
        return week_mesg

#function for find first two days weekly remienderr mesg
def load_weekly2():
    msg = mongo.db.schdulers_msg.find_one({
        "weekly_remainder2": {"$exists": True}
    }, {"weekly_remainder2": 1, '_id': 0})
    if msg is not None:
        weekly_msg2 = msg['weekly_remainder2']
        return weekly_msg2
    else:
        week_mesg2=default['weekly_remainder2']
        return week_mesg2

