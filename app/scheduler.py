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
    print("Running")
    # Finding random user who have the below condition
    users = mongo.db.users.find_one({"cron_checkin": False}, {'username': 1, 'user_Id': 1})
    print("find users profiles in cron_checkin flase")
    if users is not None:
        ID_ = users['user_Id']
        print(ID_)
        username = users['username']
        print(username)
        Id = str(users['_id'])
        print(Id)
        print("successfully find user_id")
        # update the condition to true for the particular user
        
        docs = mongo.db.users.update_one({
            "_id": ObjectId(Id)
        }, {
            "$set": {
                "cron_checkin": True
            }}, upsert=False)
        print("updated cron value  as true")
    
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
        print("Got response from hr Api")
        # getting the dates where user was present and store it in date_list
        date_list = list()
        for data in attn_data:
            attn = (data['full_date'])
            time = data['total_time']
            if time is not None:
                date_list.append(attn)
            else:
                pass
                
        # Taking the length of the date_list to find number of days user was present
        no_days_present = len(date_list)
        print('No of days present' + ' :' + str(no_days_present))
        print(date_list)
        if date_list is not None:
            first = date_list[0]
            fri_date = str(first)
            first_date = parser.parse(fri_date)
            first_date_iso = first_date.isoformat()
            
        else:
            pass
        
        # converting of ISO format of second date
        if date_list is not None:
            last = date_list[-1]
            print(last)
            lst_date = str(last)
            last_date = parser.parse(lst_date)
            last_date_iso = last_date.isoformat()
        else:
            pass
        if first_date_iso and last_date_iso is not None:
            F = datetime.datetime.strptime(first_date_iso, "%Y-%m-%dT%H:%M:%S")
            L = datetime.datetime.strptime(last_date_iso, "%Y-%m-%dT%H:%M:%S")
        else:
            F=0
            L=0    
    
        
        # Finding the days on which check_in is done
        reports = mongo.db.reports.find({
            "user": Id,
            "type": "daily",
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
def overall_reviewes():
    users = mongo.db.reports.find({"cron_checkin": True})
    print("got reports in cron_checkin true")
    users = [serialize_doc(doc) for doc in users]
    for detail in users:
        id = detail['user']
        print(id)
        print("got user id")
        docs = mongo.db.reports.update({
            "user": str(id)
        }, {
            "$set": {
                "cron_checkin": False
            }}, upsert=False)
        print("Update cron_checkin false")
        docs = mongo.db.reports.find({"user": str(id), "type": "weekly"})
        user = mongo.db.users.find_one({"_id": ObjectId(id)})
        weights = user['managers']
        all_weight = []
        for weg in weights:
            weight = weg['weight']
            all_weight.append(weight)
        docs = [serialize_doc(doc) for doc in docs]
    
        all_sum = []
        for detail in docs:
            if 'review' in detail:
                for review in detail['review']:
                    print(review)
                    all_sum.append(review['rating'])
            else:
                pass
        print("got all sum list")
        Abc = len(all_sum)
        xyz = len(all_weight)
        
        if Abc==xyz:
            print("all_sum and all weights are ==")
            weighted_avg = np.average(all_sum, weights=all_weight, )
        else:
            print("all_sum and all weights are ==")
            weighted_avg = 0    
        ret = mongo.db.users.update({
            "_id": ObjectId(id)
        }, {
            "$set": {
                "Overall_rating": weighted_avg
            }
        })
        print("Overall_rating updated  in user profile")



# Function for reseting the cron values to FALSE
def update_croncheckin():
    docs = mongo.db.users.update({
        "cron_checkin": True
    }, {
        "$set": {
            "cron_checkin": False
        }}, upsert=False, multi=True)
 
    ret = mongo.db.users.update({
        "missed_chechkin_crone": True
    }, {
        "$set": {
            "missed_chechkin_crone": False
        }}, upsert=False, multi=True)

def weekly_remainder():
    print("running")
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
        "user": {"$in": ID}
    })
    reports = [serialize_doc(doc) for doc in reports]
    user_id = []
    for data_id in reports:
        user_id.append(ObjectId(data_id['user']))
    rep = mongo.db.users.find({
        "_id": {"$nin": user_id}
    })
    rep = [serialize_doc(doc) for doc in rep]

    weekly_id = []
    if 'profileImage' and 'team' and 'job_title' in rep:
        for details in rep:
            weekly_id.append({"ID_": details['_id'], "name": details['username'],"slack_id": details['slack_id'],"profileImage": details['profileImage'],"team": details['team'],"job_title": details['job_title']})
    else:
        for details in rep:
            weekly_id.append({"ID_": details['_id'], "name": details['username'],"slack_id": details['slack_id'],"profileImage":"","team":"","job_title":""})

    for doc in weekly_id:
        ID_ = doc['ID_']
        name = doc['name']
        profileimage = doc['profileImage']
        job_title = doc['job_title']
        team = doc['team']
        slack_id = doc['slack_id']
        ret = mongo.db.recent_activity.update({
            "user": ID_},
            {"$push": {
                "weekly": {
                    "created_at": datetime.datetime.now(),
                    "priority": 1,
                    "Message": "Please create your weekly report" + ' ' + str(name)
                }}}, upsert=True)
        print("IOT")
        day = datetime.datetime.today().weekday()
        
        week_day=[0,1,2]
        last =[3,4]
        if day in week_day:
            slack_message(msg="Please create your weekly report " + ' ' +"<@"+slack_id+">!")
        elif day in last:
                slack_message(msg="Hi"+' ' +"<@"+slack_id+">!"+' ' +"You are past due your date for weekly report, you need to do your weekly report asap. Failing to do so will automatically set your weekly review to 0 which will effect your overall score.")
        else:    
            if day == 0:
                reviewed = False
                users = mongo.db.users.find({
                    "_id": ObjectId(ID_)         
                })
                users = [serialize_doc(doc) for doc in users]
                managers_data = []
                for data in users:
                    for mData in data['managers']:
                        manager_id = mData['_id']
                        mData['reviewed'] = reviewed
                        managers_data.append(mData)    
                ret = mongo.db.reports.insert_one({
                    "k_highlight": "You have not done your weekly report",
                    "extra": "You have not done your weekly report",
                    "select_days": [],
                    "user": str(ID_),
                    "username": name,
                    "created_at": datetime.datetime.utcnow(),
                    "type": "weekly",
                    "is_reviewed": managers_data,
                    "profileImage": profileimage,
                    "jobtitle": job_title,
                    "team": team,
                    "cron_review_activity":False,
                    "cron_checkin": True,
                    "weekly_cron": True,
                    "difficulty": 0
                }).inserted_id
                
                users = mongo.db.reports.find({"weekly_cron": True},{"_id": 1,"is_reviewed":1})
                users = [serialize_doc(doc) for doc in users]

                
                for user in users:
                    for a in user['is_reviewed']:
                        manager_id = a['_id']
                        weekly = user['_id']
                    
                        ret = mongo.db.reports.update({
                                    "_id": ObjectId(weekly)
                                }, {
                                    "$push": {
                                        "review": {
                                            "difficulty": 0,
                                            "rating": 0,
                                            "created_at": datetime.datetime.utcnow(),
                                            "comment": "you have not done your weekly report",
                                            "manager_id":manager_id
                                        }
                                    }
                                })

                        docs = mongo.db.reports.update({
                                "_id": ObjectId(weekly),
                                "is_reviewed": {'$elemMatch': {"_id": str(manager_id), "reviewed": False}},
                            }, {
                                "$set": {
                                    "is_reviewed.$.reviewed": True
                                }})
                    
                        cron = mongo.db.reports.update({
                            "_id": ObjectId(weekly)
                                }, {    
                            "$set": {
                                "weekly_cron": False
                                }})

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

        
        
