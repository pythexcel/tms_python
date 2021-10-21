import datetime
import requests
import dateutil.parser as parser
from app.config import URL
from bson.objectid import ObjectId
from app.util import serialize_doc
from app import mongo
import numpy as np
from app.config import notification_system_url,button,tms_system_url,easy_actions,weekly_notification,accountname

from app.util import secret_key
import uuid
import json
from bson import json_util
# schduler to caculate monthly score

def monthly_score():
    print('running...')
    # find all the reports of monthly
    reports = mongo.db.reports.find({"type": "monthly"})
    reports = [serialize_doc(doc) for doc in reports]
    for detail in reports:
        _id = detail['user']
        print(_id)
        state = mongo.db.users.find_one({
            "_id": ObjectId(_id),
            "rating_reset_time": {"$exists": True}
            }, {"rating_reset_time": 1, '_id': 0})
        if state is not None:
            reset_time = state['rating_reset_time']
            #find monthly report of one particular user
            docs = mongo.db.reports.find({"user": str(_id), "type": "monthly","created_at": {"$gte":reset_time}})
            docs = [serialize_doc(doc) for doc in docs]
        else:
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
        score = {}
        # append in dictionary all the ID with all their ratings and find len count of their ratings and append in y dict
        for data in all_sum:
            # checking if id in score dic if not add if yes add only the rating assigned to it
            if data['id'] in score:
                # here we add both the scores of one particular key and find the count/len of those rating availabel
                score[data['id']][0] = (score[data['id']][0] + data['rating'])
                score[data['id']][1] = score[data['id']][1] + 1
                # (y[data['title']] + data['rating'])
            else:
                score[data['id']] = [data['rating'], 1]
        # find all the avg of kpi/era ratings
        for elem in score:
            score[elem] = score[elem][0] / score[elem][1]
       # update the kpi/era rating in particular user profile
        ret = mongo.db.users.update({
            "_id": ObjectId(str(_id))
        }, {
            "$set": {
                "Monthly_rating": score
            }
        })
        print(ret)

        
def monthly_remainder():
    print("state_check")
    state = mongo.db.schdulers_setting.find_one({
        "monthly_remainder": {"$exists": True}
    }, {"monthly_remainder": 1, '_id': 0})
    status = state['monthly_remainder']
    if status == 1:
        today = datetime.datetime.utcnow()
        first = today.replace(day=1)
        lastMonth = first - datetime.timedelta(days=1)
        month = lastMonth.strftime("%B")
        users = mongo.db.users.find({"status": "Enabled"})
        users = [serialize_doc(user) for user in users]
    
        ID = []
        # append all users _id
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
        repp = [serialize_doc(doc) for doc in rep]
        
        monthly_id = []
        # FInd detail of user who have not done monthly report
        for details in repp:
            if 'slack_id' and 'role' and "dateofjoining" and "kpi_id" in details:
                monthly_id.append({"ID_": details['_id'], "name": details['username'], "slack_id": details['slack_id'], "role": details['role'],
                                                    "kpi_id":details['kpi_id'],"email":details['email']})
            else:
                monthly_id.append({"ID_": details['_id'], "name": details['username'], "slack_id": details['slack_id'],
                                    "role": details['role'],"email":details['email']})
    
        for doc in monthly_id:
            if "kpi_id" in doc:
                ID_ = doc['ID_']
                rep = mongo.db.reports.find({"user":ID_,"type":"weekly"})
                rwe = [serialize_doc(doc)for doc in rep]
                print(len(rwe))
                if len(rwe) >= 3:
                    role = doc['role']
                    print(role)
                    kpi_id = doc['kpi_id']
                    slack_id = doc['slack_id']
                    email = doc['email']
                    name = doc['name']
                    print(month)
                    today_date = int(today.strftime("%d"))
                    #check if user allow date(joiningdate + 10) is greater then to today date then send normal slack msg else create a report with default ratings
                    if today_date<11:
                        if role != 'Admin':
                            user = json.loads(json.dumps(doc,default=json_util.default))
                            monthly_reminder_payload = {"user":user,
                            "data":month,"message_key":"monthly_reminder","message_type":"simple_message"}
                            notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname,json=monthly_reminder_payload)
                            print('sended')
                        else:
                            print('wait')
                    else:
                        print("adding report")
                        reviewed = False
                        #Finding kpi id of current user for getting assign kpi or era details which we use in default report creation
                        kpis = mongo.db.kpi.find_one({
                            "_id": ObjectId(kpi_id)
                        })
                        kpi_json = kpis['kpi_json']
                        era_json = kpis['era_json']
                        del kpi_json[0]
                        del era_json[0]
                        kpi_j=[]
                        #adding default comment or rating 
                        for kpi in kpi_json:
                            kpi["comment"]="you have not done your monthly report"
                            kpi['rating']=0
                            kpi_j.append(kpi)
                        
                        era_j=[]
                        for era in era_json:
                            era["comment"]="you have not done your monthly report"
                            era['rating']=0
                            era_j.append(kpi)

                        print(kpi_j)
                        print(era_j)

                        #finding managers details
                        users = mongo.db.users.find({
                            "_id": ObjectId(ID_)
                        })
                        users = [serialize_doc(doc) for doc in users]
                        enb_managers = []
                        managers = mongo.db.users.find({"$or":[{"role":"manager"},{"role":"Admin"}], "status": "Enabled"
                                })
                        managers = [serialize_doc(doc) for doc in managers]
                        print(managers)
                        for data in managers:
                            enb_managers.append(data['_id'])
                        managers_data = []
                        for data in users:
                            if "managers" in data:
                                for mData in data['managers']:
                                    manager_id = mData['_id']
                                    mData['reviewed'] = reviewed
                                    if manager_id in enb_managers:
                                        managers_data.append(mData)

                        #inserting monthly report with default values.
                        ret = mongo.db.reports.insert_one({
                            "user": str(ID_),
                            "created_at": datetime.datetime.utcnow(),
                            "type": "monthly",
                            "is_reviewed": managers_data,
                            "month":month,
                            "report":{"kpi": kpi_j,"era": era_j},
                            "monthly_cron": True
                        }).inserted_id
                        
                        #finding automated created monthly reports for review by assign managers
                        users = mongo.db.reports.find({"monthly_cron": True},{"_id": 1,"is_reviewed":1})
                        users = [serialize_doc(doc) for doc in users]


                        for user in users:
                            for deta in user['is_reviewed']:
                                manager_id = deta['_id']
                                manager_weights = deta['weight']
                                monthly = user['_id']

                                #reviewing cron created monthly report by assign managers.
                                ret = mongo.db.reports.update({
                                            "_id": ObjectId(monthly)
                                        }, {
                                            "$push": {
                                                "review": {
                                                    "created_at": datetime.datetime.utcnow(),
                                                    "comment":{"kpi": kpi_j,"era": era_j},
                                                    "manager_id":manager_id,
                                                    "manager_weight":manager_weights
                                                }
                                            }
                                        })
                                #updating isreviewed option true for managers
                                docs = mongo.db.reports.update({
                                        "_id": ObjectId(monthly),
                                        "is_reviewed": {'$elemMatch': {"_id": str(manager_id), "reviewed": False}},
                                    }, {
                                        "$set": {
                                            "is_reviewed.$.reviewed": True
                                        }})

                                cron = mongo.db.reports.update({
                                    "_id": ObjectId(monthly)
                                        }, {
                                    "$set": {
                                        "monthly_cron": False
                                        }})
                                print("DONE")
                else:
                    print("NO REPORTS")
                    pass                                            
            else:
                pass


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
    secret_key1 = secret_key()
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
    

      
        # generating current month and year
        today = datetime.datetime.now()
        month = str(today.month)
        year = str(today.year)

        # passing parameters in payload to call the api
        payload = {"action": "month_attendance", "userid": ID_, "secret_key": secret_key1,
                   "month": month, "year": year}
        response = requests.post(url=URL+"attendance/API_HR/api.php", json=payload)
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
    secret_key1 = secret_key()
    # print('Disable schduler running....')
    payload_all_disabled_users_details = {"action": "show_disabled_users", "secret_key": secret_key1}
    response_all_disabled_users_details = requests.post(url=URL+"attendance/API_HR/api.php", json=payload_all_disabled_users_details)
    result_disabled = response_all_disabled_users_details.json()
    # print('fetching the list of disable users')
    disabled_names = []
    for data_disable in result_disabled:
        disabled_names.append(data_disable['id'])
    # print(disabled_names)
    sap = mongo.db.users.find({}, {"id": 1})
    sap = [serialize_doc(user) for user in sap]
    enabled_users = []
    for doc in sap:
        if "id" in doc:
            enabled_users.append(doc['id'])
    # print('fetching all the enabled users')
    # print(enabled_users)
    disable_user = []
    for element in disabled_names:
        if element in enabled_users:
            disable_user.append(element)
    # print('users who have to be disabled')
    #print(disable_user)
    if disable_user is not None:
        # print("disable_usersssssssssssssssssssssssss",len(disable_user))
        rep = mongo.db.users.update({
            "id": {"$in": disable_user}
        }, {
            "$set": {
                "status": "Disable"

            }
        }, multi=True)
        
        users_ids = mongo.db.users.find({"id": {"$in":disable_user}}, {"_id": 1})
        users_ids_list = [serialize_doc(user_id)['_id'] for user_id in users_ids]

        mongo.db.users.update({"status":"Enabled"}, {
            "$pull": {
                "managers": {
                    "_id": {"$in":users_ids_list}
                }
            }
        },multi=True)

       
def overall_reviewes():
    print("running")
    today = datetime.datetime.utcnow()
    last_monday = today - datetime.timedelta(days=today.weekday())
    users = mongo.db.users.find({"status": "Enabled"}, {"_id": 1})
    users = [serialize_doc(doc) for doc in users]
    for detail in users:
        id = detail['_id']
        state = mongo.db.users.find_one({
            "_id": ObjectId(id),
            "rating_reset_time": {"$exists": True}
            }, {"rating_reset_time": 1, '_id': 0})
        if state is not None:
            reset_time = state['rating_reset_time']
            docs = mongo.db.reports.find({
                "user": str(id), 
                "type": "weekly",
                "created_at": {
                    "$gte":reset_time
                }
            })
        else:
            docs = mongo.db.reports.find({
                "user": str(id), 
                "type": "weekly"
            })
        
        docs = [serialize_doc(doc) for doc in docs]
        if docs:
            all_sum = []
            all_weight = []
            for detail in docs:
                if 'review' in detail:
                    for review in detail['review']:
                        if 'manager_weight' in review:
                            all_sum.append(review['rating'])
                            all_weight.append(review['manager_weight'])
                        else:
                            pass
                else:
                    pass

            print(all_sum)
            print(all_weight)
            Abc = len(all_sum)
            xyz = len(all_weight)
            print(Abc)
            print(xyz)
            if Abc == xyz and Abc and xyz != 0:
                weighted_avg = np.average(all_sum, weights=all_weight, )
                print(weighted_avg)
                ret = mongo.db.users.update({
                    "_id": ObjectId(id)
                }, {
                    "$set": {
                        "Overall_rating": weighted_avg
                    }
                })
                print(ret)
            else:
                pass


        


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
    state = mongo.db.schdulers_setting.find_one({
        "weekly_remainder": {"$exists": True}
    }, {"weekly_remainder": 1, '_id': 0})
    status = state['weekly_remainder']
    if status == 1:
        print("running")
        today = datetime.datetime.today()
        last_monday = today - datetime.timedelta(days=today.weekday())
        next_day = today + datetime.timedelta(1)
        last_day = today - datetime.timedelta(1)
       # today = datetime.datetime.utcnow()
        last_sun = today - datetime.timedelta(days=(today.weekday() + 1))
        last_mon = today - datetime.timedelta(days=(today.weekday() + 8))
        users = mongo.db.users.find({"status": "Enabled"}, {"username": 1})
        users = [serialize_doc(user) for user in users]
        ID = []
        state = mongo.db.schdulers_setting.find_one({
        "weekly_automated": {"$exists": True}
        }, {"weekly_automated": 1, '_id': 0})
        status = state['weekly_automated']
        if status == 1:
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
                "_id": {"$nin": user_id},
                "status": "Enabled"
            })
            rep = [serialize_doc(doc) for doc in rep]
            weekly_id = []
            if 'profileImage' and 'team' and 'job_title' in rep:
                for details in rep:
                    weekly_id.append({"ID_": details['_id'],"email": details['email'], "name": details['username'],"slack_id": details['slack_id'],"profileImage": details['profileImage'],"team": details['team'],"job_title": details['job_title'],"role":details['role']})
            else:
                for details in rep:
                    weekly_id.append({"ID_": details['_id'], "email": details['email'], "name": details['username'],"slack_id": details['slack_id'],"role":details['role'],"profileImage":"","team":"","job_title":""})

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
                        week_day=[0,1]
                        last =[2,3]
                        if day in week_day:
                            user = json.loads(json.dumps(doc,default=json_util.default))
                            weekly_payload = {"user": user,
                                    "data": None,
                                    "message_type" : "button_message",
                                    "message_key": "automated_weekly_less",
                                    "button":weekly_notification
                                    }
                            notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname, json=weekly_payload)          
                        elif day in last:
                                user = json.loads(json.dumps(doc,default=json_util.default))
                                weekly_payload = {"user": user,
                                    "data": None,
                                    "message_type" : "button_message",
                                    "message_key": "automated_weekly",
                                    "button":weekly_notification
                                    }
                                notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname, json=weekly_payload)            
                        else:
                            if day == 4:
                                print("adding reportttttttttttttttttttttttttttt")
                                reviewed = False
                                users = mongo.db.users.find({
                                    "_id": ObjectId(ID_)
                                })
                                users = [serialize_doc(doc) for doc in users]
                                enb_managers = []
                                managers = mongo.db.users.find({"$or":[{"role":"manager"},{"role":"Admin"}], "status": "Enabled"
                                })
                                managers = [serialize_doc(doc) for doc in managers]
                                print(managers)
                                for data in managers:
                                    enb_managers.append(data['_id'])
                                managers_data = []
                                for data in users:
                                    if "managers" in data:
                                        for mData in data['managers']:
                                            manager_id = mData['_id']
                                            mData['reviewed'] = reviewed
                                            if manager_id in enb_managers:
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
                                                    "is_reviewed.$.reviewed": True,
                                                    "is_reviewed.$.is_notify": True
                                                }},upsert=True)

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
        else:
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
                "_id": {"$nin": user_id},
                "status": "Enabled"
            })
            rep = [serialize_doc(doc) for doc in rep]
            weekly_id = []
            if 'profileImage' and 'team' and 'job_title' in rep:
                for details in rep:
                    weekly_id.append({"ID_": details['_id'],"email": details['email'], "name": details['username'],"slack_id": details['slack_id'],"profileImage": details['profileImage'],"team": details['team'],"job_title": details['job_title'],"role":details['role']})
            else:
                for details in rep:
                    weekly_id.append({"ID_": details['_id'], "email":details['email'], "name": details['username'],"slack_id": details['slack_id'],"role":details['role'],"profileImage":"","team":"","job_title":""})

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
                        week_day=[0,1]
                        last =[2,3]
                        if day in week_day:
                            user = json.loads(json.dumps(doc,default=json_util.default))
                            weekly_payload = {"user": user,
                                    "data": None,
                                    "message_type" : "simple_message",
                                    "message_key": "user_weekly_reminder"}
                            notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname, json=weekly_payload)        
                            
                        elif day in last:
                                user = json.loads(json.dumps(doc,default=json_util.default))
                                weekly_payload = {"user": user,
                                    "data": None,
                                    "message_type" : "simple_message",
                                    "message_key": "user_weekly_warning_reminder"}
                                notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname, json=weekly_payload)        
                        else:
                            if day == 4:
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
                                                    "is_reviewed.$.reviewed": True,
                                                    "is_reviewed.$.is_notify": True
                                                }},upsert=True)

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
    print("state_check")
    secret_key1=secret_key()
    state = mongo.db.schdulers_setting.find_one({
        "recent_activity": {"$exists": True}
    }, {"recent_activity": 1, '_id': 0})
    status = state['recent_activity']
    if status==1:
        print("running")
        users = mongo.db.users.find({"status":"Enabled"}, {"username": 1})
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
        rep = mongo.db.users.find({"_id": {"$nin": last_day_checkin},"status":"Enabled"})
        rep = [serialize_doc(doc) for doc in rep]

        for users in rep:
            id_=users['_id']
            role = users['role']
            ID_ = users['user_Id']
            if role != 'Admin':
                # generating current month and year
                month = str(today.month)
                year = str(today.year)
                payload = {"action": "month_attendance", "userid": ID_, "secret_key": secret_key1,
                            "month": month, "year": year}
                response = requests.post(url=URL+"attendance/API_HR/api.php", json=payload)
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
                    user = json.loads(json.dumps(users,default=json_util.default))
                    missed_checkin_payload = {"user":user,
                    "data":date,"message_key":"missed_checkin_notification","message_type":"simple_message"}
                    notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname,json=missed_checkin_payload)  
            else:
                pass
                       
def review_activity(): 
    state = mongo.db.schdulers_setting.find_one({
        "review_activity": {"$exists": True}
    }, {"review_activity": 1, '_id': 0})
    status = state['review_activity']
    if status == 1:
        print("running")
        today = datetime.datetime.utcnow()
        last_monday = today - datetime.timedelta(days=today.weekday())
        # First take date time where weekly report is to be dealt with
        enb_user = []
        user = mongo.db.users.find({"status":"Enabled"})
        users = [serialize_doc(doc) for doc in user]
        for dvn in users:
            enb_user.append(dvn['_id'])

        reports = mongo.db.reports.find({"cron_review_activity": False,
                                        "type": "weekly",
                                        "user":{"$in":enb_user},
                                        "created_at": {
                    "$gte": datetime.datetime(last_monday.year, last_monday.month, last_monday.day)
                }})

        reports = [serialize_doc(doc) for doc in reports]
        managers_name = []
        for detail in reports:
            for data in detail['is_reviewed']:
                if data['reviewed'] is False:  
                    user = detail['user'] 
                    slack_id = data['_id']
                    print(slack_id)
                    checking = mongo.db.users.find_one({"_id": ObjectId(str(user)),"managers":{'$elemMatch': {"_id": str(slack_id)}}})
                    if checking is not None:
                        use = mongo.db.users.find({"_id": ObjectId(str(slack_id)),"status":"Enabled"})
                        use = [serialize_doc(doc) for doc in use]
                        for details in use:
                            if details not in managers_name:
                                managers_name.append(details)
                    else:
                        pass
        print(managers_name)
        for ids in managers_name:
            user = json.loads(json.dumps(ids,default=json_util.default))
            manager_monthly_reminder = {"user":user,
            "data":None,"message_key":"weekly_manager_reminder","message_type":"simple_message"}
            notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname,json=manager_monthly_reminder)


def missed_review_activity():
    print("running")
    state = mongo.db.schdulers_setting.find_one({
        "missed_reviewed": {"$exists": True}
    }, {"missed_reviewed": 1, '_id': 0})
    status = state['missed_reviewed']
    print(status)
    if status == 1:
        today = datetime.datetime.utcnow()
        last_monday = today - datetime.timedelta(days=today.weekday())

        enb_user = []
        user = mongo.db.users.find({"status":"Enabled"})
        users = [serialize_doc(doc) for doc in user]
        for dvn in users:
            enb_user.append(dvn['_id'])

        reports = mongo.db.reports.find({"cron_review_activity": False,
                                        "type": "weekly",
                                        "is_reviewed": {'$elemMatch': {"reviewed": False}},
                                        "user":{"$in":enb_user},
                                        "created_at": {
                    "$lt": datetime.datetime(last_monday.year, last_monday.month, last_monday.day)
                }})
        reports = [serialize_doc(doc) for doc in reports]
        managers_name = []
        all_ids = []
        if reports:
            for detail in reports:
                for data in detail['is_reviewed']:
                    if data['reviewed'] is False:
                        user = detail['user']
                        slack_id = data['_id']
                        checking = mongo.db.users.find_one({"_id": ObjectId(str(user)),"managers":{'$elemMatch': {"_id": str(slack_id)}}})
                        if checking is not None:
                            use = mongo.db.users.find({"_id": ObjectId(str(slack_id)),"status":"Enabled"})
                            use = [serialize_doc(doc) for doc in use]
                            if use:
                                for details in use:
                                    slack = details['slack_id']
                                    mang_id = details['_id']
                                    all_ids.append(details)
                                    if details not in managers_name:
                                        managers_name.append(details)
                            else:
                                pass
                        else:
                            pass
                    else:
                        pass
            print("all_ids",len(all_ids))
            print("manager_name",len(managers_name))
            if managers_name:
                for ids in managers_name:
                    coun = all_ids.count(ids)
                    user = json.loads(json.dumps(ids,default=json_util.default))
                    review_count_payload = {
                        "user": user,
                            "data": str(coun),
                            "message_type" : "simple_message",
                            "message_key": "review_count_message"
                    }
                    notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname, json=review_count_payload)
                    print(notification_message.text)
            else:
                pass
        else:
            pass
                        
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
        
        
def monthly_manager_reminder():
    state = mongo.db.schdulers_setting.find_one({
        "monthly_manager_reminder": {"$exists": True}
    }, {"monthly_manager_reminder": 1, '_id': 0})
    status = state['monthly_manager_reminder']
    if status == 1:
        print("running")
        today = datetime.datetime.utcnow()
        month = today.strftime("%B")
        # First take date time where weekly report is to be dealt with
        enb_user = []
        user = mongo.db.users.find({"status":"Enabled"})
        users = [serialize_doc(doc) for doc in user]
        reports = mongo.db.reports.find({"type": "monthly","user":{"$in":enb_user}})
        reports = [serialize_doc(doc) for doc in reports]
        managers_name = []
        print("for loop started")
        for detail in reports:
            for data in detail['is_reviewed']:
                if data['reviewed'] is False:
                    print("if reviewed is false")
                    slack_id = data['_id']
                    use = mongo.db.users.find({"_id": ObjectId(str(slack_id)),"status":"Enabled"})
                    use = [serialize_doc(doc) for doc in use]
                    for data in use:
                        slack = data['slack_id']
                        mang_id = data['_id']
                        email = data['work_email']
                        name = data['username']
                        emp_id = data['id']
                        if slack not in managers_name:
                            print("append")
                            managers_name.append(data)
        print(managers_name)
        for ids in managers_name:
            manager_monthly_reminder = {"user":ids,
            "data":None,"message_key":"monthly_manager_reminder","message_type":"simple_message"}
            notification_message = requests.post(url=notification_system_url,json=manager_monthly_reminder)




def weekly_rating_left():
    print("running_weekly_rating_left")
    #finding enabled users from db
    today = datetime.datetime.utcnow()
    last_monday = today - datetime.timedelta(days=today.weekday())
    enb_user = []
    user = mongo.db.users.find({"status":"Enabled"})
    users = [serialize_doc(doc) for doc in user]
    for dvn in users:
        enb_user.append(dvn['_id'])
    #finding reports of anabled users
    print("11111445555")
    reports = mongo.db.reports.find({"cron_review_activity": False,
                                    "type": "weekly",
                                    "user":{"$in":enb_user}
                                    })

    reports = [serialize_doc(doc) for doc in reports]
    #finding managers which are managers at the current time and reports available to review
    managers_name = []
    for detail in reports:
        for data in detail['is_reviewed']:
            print(detail)
            if data['reviewed'] is False:  
            
                user = detail['user']
                slack_id = data['_id']
                print(slack_id)
                # checking = mongo.db.users.find_one({"_id": ObjectId(str(user)),"status":"Enabled","managers":{'$elemMatch': {"_id": str(slack_id)}}})
                checking = mongo.db.users.find_one({"_id": ObjectId(str(user)),"status":"Enabled"})
                print(checking)
                if checking is not None:
                    print("jghf",slack_id)
                    # use = mongo.db.users.find({"_id": ObjectId(str(slack_id)),"status":"Enabled"})
                    use = mongo.db.users.find({"_id": ObjectId(str(user)),"status":"Enabled"})
                    # use = [serialize_doc(doc) for doc in use]
                    print("hgdkgf", use)
                    for details in use:
                        if details not in managers_name:
                            managers_name.append(details['managers'])
                else:
                    pass
    print("manager name",managers_name[0])

    #find a random reports for send to manager on slack
    for ids in managers_name[0]:
        print("asdngasvdashgdafdhagdfahdgafdahgdafdahdasdafhdah")
        id = ids['_id']
        lst_date = str("2020-01-20")
        last_date = parser.parse(lst_date)
        print(last_date)
        last_date_iso = last_date.isoformat()
        print(last_date_iso)
        F = datetime.datetime.strptime(last_date_iso, "%Y-%m-%dT%H:%M:%S")
        print(F)
        dab = mongo.db.reports.find_one({
                "type": "weekly",
                "is_reviewed": {'$elemMatch': {"_id": str(id),"reviewed":False}},
                "created_at": {
                    "$gte":F,
            }
            })
        print(dab)
        #finding require detials and sending report and msg to manager
        if dab is not None:
            weekly_id = dab['_id']
            k_highlight = dab['k_highlight']
            extra = dab['extra']
            junior_id = dab['user']
            report = dab['report']
            descriptio = k_highlight[0]
            # description = k_highlight
            description = descriptio['description']
            user_details = mongo.db.users.find_one({"_id":ObjectId(junior_id),"status":"Enabled"},{"_id":0,"username":1})
            print(user_details)
            if user_details is not None:
                print("user is not none")
                username = user_details['username']
                for manager_obj in dab['is_reviewed']:
                    manager_id = manager_obj['_id']
                    if manager_id == str(id):
                        mang_id = manager_id
                        expire_time = manager_obj['expire_time']
                        unique_id = manager_obj['expire_id']
                        state = mongo.db.schdulers_setting.find_one({
                            "easyRating": {"$exists": True}
                            }, {"easyRating": 1,'_id': 0})
                        status = state['easyRating']

                        manager_profile = mongo.db.users.find_one({
                            "_id": ObjectId(str(mang_id))
                                })
                        manager_profile["_id"] = str(manager_profile["_id"])

                        actions = button['actions']
                        easy_action = easy_actions['actions']

                        docs = mongo.db.reports.update({
                            "_id": ObjectId(weekly_id),
                            "type":"weekly",
                            "is_reviewed": {'$elemMatch': {"_id": str(mang_id)}},
                        }, {
                            "$set": {
                                "is_reviewed.$.is_notify": True,
                                "is_reviewed.$.expire_time":datetime.datetime.now() + datetime.timedelta(minutes=15)
                            }})

                        if status == 1:
                            print("iffffffffffffffffffffffffffffffffffffffffffff")
                            for action in easy_action:
                                value = action['text']
                                if value == "Bad":
                                    rating = "3"
                                if value == "Neutral":
                                    rating = "5"
                                if value == "Good":
                                    rating = "8"
                                api_url = ""+tms_system_url+"slack_report_review?rating="+rating+"&comment=""&weekly_id="+str(weekly_id)+"&manager_id="+mang_id+"&unique_id="+unique_id+""
                                action["url"] = api_url
                            user = json.loads(json.dumps(manager_profile,default=json_util.default))
                            extra_with_msg = (extra +"\nYou can review weekly reports directly from slack now! Just select the rating below.")
                            weekly_payload = {"user":user,
                            "data":{"junior":username, "report":report, "extra":extra_with_msg},"message_key":"weekly_notification","message_type":"button_message","button":easy_actions}
                            notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname,json=weekly_payload)
                        else:
                            print("elseeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee")
                            for action in actions:
                                rating = action['text']
                                api_url = ""+tms_system_url+"slack_report_review?rating="+rating+"&comment=""&weekly_id="+str(weekly_id)+"&manager_id="+mang_id+"&unique_id="+unique_id+""
                                action["url"] = api_url
                            user = json.loads(json.dumps(manager_profile,default=json_util.default))
                            extra_with_msg = (extra +"\nYou can review weekly reports directly from slack now! Just select the rating below.")
                            weekly_payload = {"user":user,
                            "data":{"junior":username, "report":description , "extra":extra_with_msg},"message_key":"weekly_notification","message_type":"button_message","button":button}
                            notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname,json=weekly_payload)
            else:
                pass
        else:
            pass
