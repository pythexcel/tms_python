import datetime
import requests
import dateutil.parser as parser
from app.config import attn_url, secret_key
from bson.objectid import ObjectId
from app.util import serialize_doc
from app import mongo
import numpy as np
from app.util import slack_message


def checkin_score():
    print("checkin score running")
    # Finding random user who have the below condition
    users = mongo.db.users.find_one({"cron_checkin": False}, {'username': 1, 'user_Id': 1})
    if users is not None:
        ID_ = users['user_Id']
        print(ID_)
        Id = str(users['_id'])
        print(Id)

        # update the condition to true for the particular user
        docs = mongo.db.users.update_one({
            "cron_checkin": False
        }, {
            "$set": {
                "cron_checkin": True
            }}, upsert=False)

        URL = attn_url
        # generating current month and year
        today = datetime.datetime.now()
        month = str(today.month)
        year = str(today.year)

        # passing parameters in payload to call the api
        payload = {"action": "month_attendance", "userid": ID_, "secret_key": secret_key,
                   "month": month, "year": year}
        response = requests.post(url=URL, json=payload)
        data = response.json()
        attn_data = data['data']['attendance']

        # getting the dates where user was present and store it in date_list
        date_list = list()
        for data in attn_data:
            attn = (data['full_date'])
            if len(data['total_time']) > 0:
                date_list.append(attn)

        # Taking the length of the date_list to find number of days user was present
        no_days_present = len(date_list)
        print('No of days present' + ' :' + str(no_days_present))

        # converting of ISO format of first date
        first = date_list[0]
        fri_date = str(first)
        first_date = parser.parse(fri_date)
        first_date_iso = first_date.isoformat()

        # converting of ISO format of second date
        last = date_list[-1]
        lst_date = str(last)
        last_date = parser.parse(lst_date)
        last_date_iso = last_date.isoformat()

        F = datetime.datetime.strptime(first_date_iso, "%Y-%m-%dT%H:%M:%S")
        L = datetime.datetime.strptime(last_date_iso, "%Y-%m-%dT%H:%M:%S")

        # Finding the days on which check_in is done
        reports = mongo.db.reports.find({
            "user": Id,
            "created_at": {
                "$gte": F,
                "$lte": L
            }
        })
        reports = [serialize_doc(report) for report in reports]

        # storing just the check-in dates from reports in no_of_checking list
        no_of_checking = list()
        for data in reports:
            no_of_checking.append(data['created_at'])

        # Taking the length of the list and store it in no_of_checking_days list
        list_checkin = no_of_checking
        no_of_checking_days = len(list_checkin)
        print('No of days checkin done' + ' :' + str(no_of_checking_days))

        # Calculating the overall_score for checkin of a user
        checkin_scr = ((no_of_checking_days* 100) / no_days_present)
        print('overall_score' + ' :' + str(checkin_scr))
        ret = mongo.db.users.update({
            "_id": ObjectId(Id)
        }, {
            "$set": {
                "Checkin_rating": checkin_scr,
            }
        })
    else:
        return 'Job done'

# Function for overall review of a user
def overall_reviewes():
    print("overall reviews running")
    users = mongo.db.reports.find({"cron_checkin":True})
    users = [serialize_doc(doc) for doc in users]
    for detail in users:
        id=detail['user']
        print(id)
        docs = mongo.db.reports.update({
        "user":str(id)
        }, {
        "$set": {
           "cron_checkin": False
           }}, upsert=False)
        docs = mongo.db.reports.find({"user": str(id), "type": "weekly"})
        user = mongo.db.users.find_one({"_id": ObjectId(id)})
        weights = user['managers']
        all_weight = []
        for weg in weights:
            weight = weg['weight']
            all_weight.append(weight)
        print(all_weight)
        docs = [serialize_doc(doc) for doc in docs]
        print(docs)
        all_sum = []
        for detail in docs:
            for review in detail['review']:
                print(review)
                all_sum.append(review['rating'])

        print(all_sum)
        weighted_avg = np.average(all_sum, weights=all_weight, )
    
        ret = mongo.db.users.update({
            "_id": ObjectId(id)
        }, {
            "$set": {
                "Overall_rating": weighted_avg
            }
        })



# Function for reseting the cron values to FALSE
def update_croncheckin():
    print("update cron checkin running")
    docs = mongo.db.users.update({
        "cron_checkin": True
    }, {
        "$set": {
            "cron_checkin": False
        }}, upsert=False, multi=True)

    ret = mongo.db.reports.update({
        "cron_checkin": False
    }, {
        "$set": {
            "cron_checkin": True
        }}, upsert=False, multi=True)

    ret = mongo.db.users.update({
        "missed_chechkin_crone": True
    }, {
        "$set": {
            "missed_chechkin_crone": False
        }}, upsert=False, multi=True)

def recent_activity():
    print("recent activity running")
    users = mongo.db.reports.find({"type": "daily"})
    users = [serialize_doc(doc) for doc in users]
    print(users)
    # find user id
    for detail in users:
        ID = detail['user']
        print(ID)
        today = datetime.datetime.now()
        print(today)
        last_day = today - datetime.timedelta(1)
        print(last_day)
        # find reports checkin by user_id
        reports = mongo.db.reports.find({
            "user": str(ID),
            "type": "daily",
            "created_at": {
                "$gte": datetime.datetime(last_day.year, last_day.month, last_day.day),
                "$lte": datetime.datetime(today.year, today.month, today.day)
            }
        })
        reports = [serialize_doc(report) for report in reports]
        print('asdsadsa')
        # if checkin not found update date in user profile
        users = mongo.db.users.find_one({"_id": ObjectId(str(ID)),
                                         "missed_chechkin_crone":False,
                                         "daily_chechkin_mandatory": {"$exists": False}},
                                        {'username': 1, 'user_Id': 1})
        if users is not None:
            username = users['username']
            ID_ = users['user_Id']
            URL = attn_url
            dec = mongo.db.users.update({
                "_id": ObjectId(str(ID))
            }, {
                "$set": {
                    "missed_chechkin_crone": True
                }})

            # generating current month and year
            month = str(today.month)
            year = str(today.year)
            payload = {"action": "month_attendance", "userid": ID_, "secret_key": secret_key,
                       "month": month, "year": year}
            response = requests.post(url=URL, json=payload)
            data = response.json()
            attn_data = data['data']['attendance']


            # getting the dates where user was present and store it in date_list
            date_list = list()
            date_time = today - datetime.timedelta(1)
            date = date_time.strftime("%Y-%m-%d")

            for data in date_list:
                attn = (data['full_date'])
                if len(data['total_time']) > 0:
                    date_list.append(attn)
            if date not in date_list:
                ret = mongo.db.users.update({
                    "_id": ObjectId(str(ID))},
                    {"$push": {"missed_checkin_dates": {
                        "date": date,
                        "created_at": datetime.datetime.now()
                    }}})
                print(ret)
                docs = mongo.db.recent_activity.update({
                    "user": str(ID)},
                    {"$push": {"missed_checkin": {
                        "checkin_message": date_time,
                        "created_at": datetime.datetime.now(),
                        "priority": 1

                    }}}, upsert=True)
                slack_message(msg=username + " "+'have missed '+str(date)+'check-in')

def review_activity():
    print("review activity running")
    # First take date time where weekly report is to be dealt with
    today = datetime.date.today()
    last_sunday = today - datetime.timedelta(days=(today.weekday() + 1))
    last_monday = today - datetime.timedelta(days=(today.weekday() + 8))
    # find user by a common variable
    #users = mongo.db.reports.find({"cron_recent_activity": False})
    #cron_review_activity
    users = mongo.db.reports.find({"cron_review_activity": False})
    users = [serialize_doc(doc) for doc in users]
    print(len(users))
    for detail in users:
        ID = detail['user']
        
        # update cron  variable True
        docs = mongo.db.reports.update({
            "user": ID
        }, {
            "$set": {
                "cron_review_activity":True
            }})
    
    # find user id
        
    ID = []
    for detail in users:
        ID.append(ObjectId(detail['user']))
    # find in users for manager details
    print(ID)
    docs = mongo.db.users.find({
        "_id": {"$in": ID}})
    docs = [serialize_doc(doc) for doc in docs]
    print("304")
    manage = []
    for data in docs:
        for data in data['managers']:
            manage.append(data['_id'])
    print(manage)
    # find manager id
    # First find the users which have the manager id in it's document
    users = mongo.db.users.find({
        "managers": {
            "$elemMatch": {"_id": {"$in": manage}}
        }
    })
    users = [serialize_doc(doc) for doc in users]
    # Make a list of User_id and then fetch all the users/juniors belong to that manager
    user_ids = []
    name_list = []
    for user in users:
        user_ids.append(str(user['_id']))
        name_list.append(user['username'])
    
    # Now find weekly reports of all those users_id in the above list whose report is not reviewd


    for data in user_ids:
        print(data)
        #find({"$and":[ {"vals":100}, {"vals":1100}]})
        docs = mongo.db.reports.find({"$and":[{"user": data},{"cron_review_activity":True},{"review": {'$exists': False}},{"created_at": {
                "$gte": datetime.datetime(last_monday.year, last_monday.month, last_monday.day),
                "$lte": datetime.datetime(last_sunday.year, last_sunday.month, last_sunday.day)
            }}]
        }, {"user": 1})
        docs = [serialize_doc(doc) for doc in docs]
        # Append those user records whose not been reviewd in user_id list


        #for junior_name in name_list:
            #print(junior_name)
            # Then if we find that data exist in user_id report than update the manager recent activity with a date and message
            #if junior_name is not None:
    for data in manage:
    
        ret = mongo.db.recent_activity.update({
            "user": data},
                {"$push": {
                "review_report": {
                    "created_at": datetime.datetime.now(),
                    "priority": 1,
                    "Message": "You have to review your Junior "" " + str(name_list) + "weekly report"
                    }}}, upsert=True)
        slack_message(msg=str(data) + " " + 'you have to review your Junior ' + str(name_list) + 'weekly report')

        
def weekly_remainder():
    today = datetime.datetime.today()
    next_day = today + datetime.timedelta(1)
    last_day = today - datetime.timedelta(1)
    users = mongo.db.users.find({}, {"username": 1})
    users = [serialize_doc(user) for user in users]
    ID = []
    for data in users:
        ID.append(data['_id'])
    reports = mongo.db.reports.find({
        "type": "weekly",
        "user": {"$in": ID},
        "created_at": {
                "$gt": datetime.datetime(last_day.year, last_day.month, last_day.day),
                "$lt": datetime.datetime(next_day.year, next_day.month, next_day.day)
            }
    })
    reports = [serialize_doc(doc) for doc in reports]
    user_id = []
    for data_id in reports:
        user_id.append(ObjectId(data_id['user']))

    rep = mongo.db.users.find({
        "_id": {"$nin": user_id}
    }, {"username": 1})
    rep = [serialize_doc(doc) for doc in rep]

    weekly_id = []
    for details in rep:
        weekly_id.append({"ID_": details['_id'], "name": details['username']})
    for doc in weekly_id:
        ID_ = doc['ID_']
        name = doc['name']
        ret = mongo.db.recent_activity.update({
            "user": ID_},
            {"$push": {
                "weekly": {
                    "created_at": datetime.datetime.now(),
                    "priority": 1,
                    "Message": "Please create your weekly report" + ' ' + str(name)
                }}}, upsert=True)
        slack_message(msg="Please create your weekly report " + ' ' + name)
        
        
