import datetime
import requests
import dateutil.parser as parser
from app.config import attn_url, secret_key
from bson.objectid import ObjectId
from app.util import serialize_doc
from app import mongo
import numpy as np
from app.util import slack_message
import uuid

def monthly_score():
    print('running...')
    # find all the reports of monthly
    reports = mongo.db.reports.find({"type": "monthly"})
    reports = [serialize_doc(doc) for doc in reports]
    for detail in reports:
        _id = detail['user']
        print(_id)
        #find monthly report of one particular user
        docs = mongo.db.reports.find({"user": str(_id), "type": "monthly"})
        docs = [serialize_doc(doc) for doc in docs]
        print(docs)
        # append in all_sum arrays all the ID of kpi/era and their rating
        all_sum = []
        for detail in docs:
            if 'review' in detail:
                for review in detail['review']:
                    for data in review['comment']['kpi']:
                        all_sum.append({'id': data['id'], 'rating': data['rating']})
                    for data in review['comment']['era']:
                        all_sum.append({'id': data['id'], 'rating': data['rating']})

        print(all_sum)
        y = {}
        # append in dictionary all the ID with all their ratings and find len count of their ratings and append in y dict
        for data in all_sum:
            if data['id'] in y:

                y[data['id']][0] = (y[data['id']][0] + data['rating'])
                y[data['id']][1] = y[data['id']][1] + 1
                # (y[data['title']] + data['rating'])

            else:
                y[data['id']] = [data['rating'], 1]
        # find all the avg of kpi/era ratings
        for elem in y:
            y[elem] = y[elem][0] / y[elem][1]
       # update the kpi/era rating in particular user profile
        ret = mongo.db.users.update({
            "_id": ObjectId(str(_id))
        }, {
            "$set": {
                "Monthly_rating": y
            }
        })
        print(ret)

def monthly_remainder():
    print("running")
    today = datetime.datetime.utcnow()
    month = today.strftime("%B")
    #find all the users 
    users = mongo.db.users.find({"status": "Enabled"}, {"username": 1})
    users = [serialize_doc(user) for user in users]
    ID = []
    #append all users _id
    for data in users:
        ID.append(data['_id'])
    # find the monthly reports of all the user     
    reports = mongo.db.reports.find({
        "type": "monthly",
        "user": {"$in": ID},
        "month": month
    })
    reports = [serialize_doc(doc) for doc in reports]
    user_id = []
    for data_id in reports:
        user_id.append(ObjectId(data_id['user']))
    # find the users who have not done monthly report    
    rep = mongo.db.users.find({
        "_id": {"$nin": user_id},
        "status": "Enabled"
    })
    rep = [serialize_doc(doc) for doc in rep]
    monthly_id = []
    # FInd detail of user who have not done monthly report
    if 'profileImage' and 'team' and 'job_title' in rep:
        for details in rep:
            monthly_id.append({"ID_": details['_id'], "name": details['username'], "slack_id": details['slack_id'],
                              "profileImage": details['profileImage'], "team": details['team'],
                              "job_title": details['job_title'], "role": details['role'],"dateofjoining": details['dateofjoining']})
    else:
        for details in rep:
            monthly_id.append({"ID_": details['_id'], "name": details['username'], "slack_id": details['slack_id'],
                              "role": details['role'], "profileImage": "", "team": "", "job_title": ""})
    for doc in monthly_id:
        role = doc['role']
        slack_id = doc['slack_id']
        doj = doc['dateofjoining']
        date = datetime.datetime.strptime(doj, "%Y-%m-%d %H:%M:%S")
        datee = date.day
        join_date = datee - 3
        today_date = int(today.strftime("%d"))
        print(join_date)
        # check of date of joinging of the user if today's date is just 3 days befor the user join date send him reminder else no reminder
        if today_date > join_date:
            if role != 'Admin':
                slack_message(msg="Please create your monthly report " + ' ' + "<@" + slack_id + ">!")
                print('sended')
        else:
            print('wait')
                
def random_kpi():
    docs = mongo.db.kpi.find({})
    docs = [serialize_doc(doc) for doc in docs]
    for details in docs:
        for elem in details['era_json']:
            elem['ID'] = uuid.uuid4().hex
        for data in details['kpi_json']:
            data['ID'] = uuid.uuid4().hex
            for elem in docs:
                ID = ObjectId(elem['_id'])
                print(ID)
                era_json = elem['era_json']
                kpi_json = elem['kpi_json']
                kpi_name = elem['kpi_name']
                print(kpi_name)

                ret = mongo.db.kpi.update({
                    "_id": ID},
                    {"$set":
                        {
                            "era_json": era_json,
                            "kpi_json": kpi_json,
                            "kpi_name": kpi_name
                        }})

                print(ret)

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
            attn = data['full_date']
            intime = data['out_time']          
            if intime:
                date_list.append(attn)
        print(date_list)
        # Taking the length of the date_list to find number of days user was present
        no_days_present = len(date_list)
        print('No of days present' + ' :' + str(no_days_present))
        if no_days_present != 0:
            first = date_list[0]
            fri_date = str(first)
            first_date = parser.parse(fri_date)
            first_date_iso = first_date.isoformat()  
        else:
            first_date_iso = 0
        
        # converting of ISO format of second date
        if no_days_present != 0:
            last = date_list[-1]
            print(last)
            lst_date = str(last)
            last_date = parser.parse(lst_date)
            last_date_iso = last_date.isoformat()
        else:
            last_date_iso=0
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

        if no_days_present != 0:
        # Calculating the overall_score for checkin of a user
            checkin_scr = ((no_of_checking_days* 100) / no_days_present)
            print('overall_score' + ' :' + str(checkin_scr))
        else:
            checkin_scr = 0

        ret = mongo.db.users.update({
            "_id": ObjectId(Id)
        }, {
            "$set": {
                "Checkin_rating": checkin_scr,
            }
        })
        
        
def disable_user():
    print('Disable schduler running....')
    payload_all_disabled_users_details = {"action": "show_disabled_users", "secret_key": secret_key}
    response_all_disabled_users_details = requests.post(url=attn_url, json=payload_all_disabled_users_details)
    result_disabled = response_all_disabled_users_details.json()
    print('fetching the list of disable users')
    disabled_names = []
    for data_disable in result_disabled:
        disabled_names.append(data_disable['id'])
    print(disabled_names)
    sap = mongo.db.users.find({}, {"id": 1})
    sap = [serialize_doc(user) for user in sap]
    enabled_users = []
    for doc in sap:
        enabled_users.append(doc['id'])
    print('fetching all the enabled users')
    print(enabled_users)
    disable_user = []
    for element in disabled_names:
        if element in enabled_users:
            disable_user.append(element)
    print('users who have to be disabled')
    print(disable_user)
    if disable_user is not None:
        rep = mongo.db.users.update({
            "id": {"$in": disable_user}
        }, {
            "$set": {
                "status": "Disable"

            }
        }, multi=True)
        print(rep)
       
       
def overall_reviewes():
    print("running")
    today = datetime.datetime.utcnow()
    last_monday = today - datetime.timedelta(days=today.weekday())
    users = mongo.db.reports.find({"type": "weekly"})
    users = [serialize_doc(doc) for doc in users]
    for detail in users:
        id = detail['user']

        docs = mongo.db.reports.find({"user": str(id), "type": "weekly"})
        docs = [serialize_doc(doc) for doc in docs]

        p_difficulty = []
        all_sum = []
        all_weight = []
        for detail in docs:
            if 'review' in detail:
                for review in detail['review']:
                    all_sum.append(review['rating'])
                    p_difficulty.append(review['difficulty'])
                    all_weight.append(review['manager_weight'])
            else:
                pass

        print(all_sum)
        print(all_weight)
        print("got all sum list")
        difficulty_len = len(p_difficulty)
        p_sum = sum(p_difficulty)
        if difficulty_len and p_sum != 0:
            project_difficulty = (p_sum / difficulty_len)
        else:
            pass

        Abc = len(all_sum)
        xyz = len(all_weight)

        if Abc == xyz:
            weighted_avg = np.average(all_sum, weights=all_weight, )
        else:
            print("all_sum and all weights are !=")
            weighted_avg = 0
        print(weighted_avg)
        ret = mongo.db.users.update({
            "_id": ObjectId(id)
        }, {
            "$set": {
                "Overall_rating": weighted_avg,
                "project_difficulty": project_difficulty
            }
        })


        


# Function for reseting the cron values to FALSE
def update_croncheckin():
    docs = mongo.db.users.update({
        "cron_checkin": True
    }, {
        "$set": {
            "cron_checkin": False
        }},multi=True)
    
    ret = mongo.db.users.update({
        "missed_chechkin_crone": True
    }, {
        "$set": {
            "missed_chechkin_crone": False
        }},multi=True)

    
def weekly_remainder():
    print("running")
    today = datetime.datetime.today()
    last_monday = today - datetime.timedelta(days=today.weekday())
    next_day = today + datetime.timedelta(1)
    last_day = today - datetime.timedelta(1)
   # today = datetime.datetime.utcnow()
    last_sun = today - datetime.timedelta(days=(today.weekday() + 1))
    last_mon = today - datetime.timedelta(days=(today.weekday() + 8))
    users = mongo.db.users.find({}, {"username": 1})
    users = [serialize_doc(user) for user in users]
    ID = []

    for data in users:
        ID.append(data['_id'])
    reports = mongo.db.reports.find({
        "type": "weekly",
        "user": {"$in":ID},
        "created_at": {
                "$gte": datetime.datetime(last_monday.year, last_monday.month, last_monday.day)
            }
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
            weekly_id.append({"ID_": details['_id'], "name": details['username'],"slack_id": details['slack_id'],"profileImage": details['profileImage'],"team": details['team'],"job_title": details['job_title'],"role":details['role']})
    else:
        for details in rep:
            weekly_id.append({"ID_": details['_id'], "name": details['username'],"slack_id": details['slack_id'],"role":details['role'],"profileImage":"","team":"","job_title":""})
    
    for doc in weekly_id:
        ID_ = doc['ID_']
        print(ID_)
        repp = mongo.db.reports.find({
            "user": str(ID_),
            "type":"daily",
            "created_at": {
            "$gte": datetime.datetime(last_mon.year, last_mon.month, last_mon.day),
            "$lte": datetime.datetime(last_sun.year, last_sun.month, last_sun.day)
        }
        })
        repp = [serialize_doc(doc) for doc in repp]
        print(len(repp))
        if repp:
            name = doc['name']
            profileimage = doc['profileImage']
            job_title = doc['job_title']
            team = doc['team']
            role=doc['role']
            slack_id = doc['slack_id']
            ret = mongo.db.recent_activity.update({
                "user": ID_},
                {"$push": {
                    "weekly": {
                        "created_at": datetime.datetime.now(),
                        "priority": 1,
                        "Message": "Please create your weekly report" + ' ' + str(name)
                    }}}, upsert=True)

            if role != 'Admin':
                day = datetime.datetime.today().weekday()

                week_day=[0,1,2]
                last =[3,4]
                if day in week_day:
                    slack_message(msg="Please create your weekly report " + ' ' +"<@"+slack_id+">!")
                elif day in last:
                        slack_message(msg="Hi"+' ' +"<@"+slack_id+">!"+' ' +"You are past due your date for weekly report, you need to do your weekly report asap. Failing to do so will automatically set your weekly review to 0 which will effect your overall score.")
                else:
                    if day == 5:
                        print("adding reportttttttttttttttttttttttttttt")
                        reviewed = False
                        users = mongo.db.users.find({
                            "_id": ObjectId(ID_)
                        })
                        users = [serialize_doc(doc) for doc in users]
                        managers_data = []
                        for data in users:
                            if "managers" in data:
                                for mData in data['managers']:
                                    manager_id = mData['_id']
                                    mData['reviewed'] = reviewed
                                    managers_data.append(mData)
                        ret = mongo.db.reports.insert_one({
                            "k_highlight": [],
                            "extra": "No comment",
                            "select_days": [],
                            "user": str(ID_),
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
                            for deta in user['is_reviewed']:
                                manager_id = deta['_id']
                                manager_weights = deta['weight']
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
                                                    "manager_id":manager_id,
                                                    "manager_weight":manager_weights
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
            else:
                pass
        else:
            pass

                        
                        
# Function of recent_activity for checkin_missed and reviewed.
def recent_activity():
    print("running")
    users = mongo.db.users.find({}, {"username": 1})
    users = [serialize_doc(doc) for doc in users]
    today = datetime.datetime.now()
    last_day = today - datetime.timedelta(1)
    last_day_checkin=[]
    for detail in users:
        ID = detail['_id']
        reports = mongo.db.reports.find_one({
            "user": str(ID),
            "type": "daily",
            "created_at": {
                "$gte": datetime.datetime(last_day.year, last_day.month, last_day.day),
                "$lte": datetime.datetime(today.year, today.month, today.day)
            }
        })
        if reports is not None:
            user=reports['user']
            last_day_checkin.append(ObjectId(user))
    print(last_day_checkin)
    rep = mongo.db.users.find({
            "_id": {"$nin": last_day_checkin}
        })
    rep = [serialize_doc(doc) for doc in rep]
    
    for users in rep:
        id_=users['_id']
        username = users['username']
        print(username)
        slack_id = users['slack_id']
        role = users['role']
        ID_ = users['user_Id']
        URL = attn_url
        if role != 'Admin':
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

            for data in attn_data:
                attn = data['full_date']
                intime = data['in_time']       
                if intime:
                    date_list.append(attn)
            print(date_list)
            if date in date_list:
                ret = mongo.db.users.update({
                    "_id": ObjectId(str(id_))},
                    {"$push": {"missed_checkin_dates": {
                        "date": date,
                        "created_at": datetime.datetime.now()
                    }}})
                                
                docs = mongo.db.recent_activity.update({
                    "user": str(id_)},
                    {"$push": {"missed_checkin": {
                        "checkin_message": date_time,
                        "created_at": datetime.datetime.now(),
                        "priority": 1

                    }}}, upsert=True)
                slack_message(msg="Hi"+' ' +"<@"+slack_id+">!"+' '+"you have missed "+str(date)+"check-in")   
        else:
            pass
                
                
                
def review_activity(): 
    print("running")
    today = datetime.datetime.utcnow()
    last_monday = today - datetime.timedelta(days=today.weekday())
    # First take date time where weekly report is to be dealt with
    reports = mongo.db.reports.find({"cron_review_activity": False,
                                    "type": "weekly",
                                    "created_at": {
                "$gte": datetime.datetime(last_monday.year, last_monday.month, last_monday.day)
            }})
   
    reports = [serialize_doc(doc) for doc in reports]
    managers_name = []
    for detail in reports:
        for data in detail['is_reviewed']:
            if data['reviewed'] is False:
                username = detail['username']    
                slack_id = data['_id']
                print(slack_id)
                use = mongo.db.users.find({"_id": ObjectId(str(slack_id))})
                use = [serialize_doc(doc) for doc in use]
                for data in use:
                    slack = data['slack_id']
                    mang_id = data['_id']
                    if slack not in managers_name:
                        managers_name.append(slack)
                        ret = mongo.db.recent_activity.update({
                            "user": mang_id},
                            {"$push": {
                            "weekly_reviewed": {
                            "created_at": datetime.datetime.utcnow(),
                            "priority": 1,
                            "Message": "You have to review your Juniors weekly report"
                            }}}, upsert=True)                
    for ids in managers_name:    
        slack_message(msg= "Hi"+' ' +"<@"+ids+">!"+' ' +"you have weekly report's pending to be reviewed") 

 
def manager_update():
    print("running")
    users = mongo.db.users.find()
    users = [serialize_doc(doc) for doc in users]
    for detail in users:
        id = detail['_id']
        print(id)
        docs = mongo.db.reports.find(
            {"user": str(id), "type": "weekly", "review": {'$elemMatch': {"manager_weight": {"$exists": False}}}})
        docs = [serialize_doc(doc) for doc in docs]
        print("fetched the reports which needed to be updated")
        print(docs)
        print(len(docs))
        if docs is not None:
            for data in docs:
                _id = data["_id"]
                managers_data = []
                for mData in data['is_reviewed']:
                    managers_data.append({"id": mData['_id'], "weight": mData['weight']})
                print(managers_data)
                print("here comes the manager data")
                for idss in managers_data:
                    manager_id = idss['id']
                    print("Manager whos weight is to be added")
                    print(manager_id)
                    m_weight = idss['weight']
                    print(m_weight)
                    print("weight which needs to be updated")
                    ret = mongo.db.reports.update({
                       "_id": ObjectId(str(_id)),
                        "review": {'$elemMatch': {"manager_id": str(manager_id)}
                                   }}, {
                        "$set": {
                            "review.$.manager_weight": m_weight}
                    }
                    )
                    print(ret)
                    print("updated")
        
