from app import token
from app import mongo
from app.util import serialize_doc, get_manager_profile,load_weekly_notes
from flask import (
    Blueprint, flash, jsonify, abort, request
)
from app.config import notification_system_url,button,tms_system_url,default_skip_settings,easy_actions,weekly_page_link,accountname
import dateutil.parser
from bson.objectid import ObjectId
import requests
from app.util import get_manager_juniors
from datetime import timedelta
import datetime
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity, get_current_user, jwt_refresh_token_required,
    verify_jwt_in_request
)
import json
from bson import json_util
import uuid

bp = Blueprint('report', __name__, url_prefix='/')


@bp.route('/user_daily', methods=["POST"])
def user_daily():
    date = request.json.get('date',None)
    username = request.json.get('username',None)
    if date and username is None:
        return jsonify({"message": "please provide date and username values"}), 400
    parsed_date = dateutil.parser.parse(date)
    date_iso = parsed_date.isoformat()
    next_day = parsed_date + datetime.timedelta(1)
    iso_date = next_day.isoformat()
    First_date = datetime.datetime.strptime(date_iso, "%Y-%m-%dT%H:%M:%S")
    Last_date = datetime.datetime.strptime(iso_date, "%Y-%m-%dT%H:%M:%S")
    ret = mongo.db.reports.find_one({"type" : "daily", "username": username, 
    "created_at": {
                    "$gt": First_date,
                    "$lt": Last_date
                }
    })
    if ret is not None:
        ret['_id'] = str(ret['_id'])
        return jsonify(ret), 200
    else:
        return jsonify({"message" : "no report available"}), 200

@bp.route('/slack', methods=["GET"])
@jwt_required
def slack():
    current_user = get_current_user()
    slack = current_user['email']
    mail_payload = {"email":slack}
    slack_channels = requests.post(url=notification_system_url+"slackchannels?account-name="+accountname,json=mail_payload).json()
    return jsonify (slack_channels)


#Api for weekly report review on slack

@bp.route('/slack_report_review', methods=["GET"])
def slack_report_review():
    rating = request.args.get('rating',default=0, type=int)
    comment = request.args.get('comment',default="", type=str)
    weekly_id = request.args.get('weekly_id',default=None, type=str)
    manager_id = request.args.get('manager_id',default=None, type=str)
    expire_id = request.args.get('unique_id',default=None, type=str)
    
    #finding manager juniours
    juniors = get_manager_juniors(manager_id)
    sap = mongo.db.reports.find_one({
                            "_id": ObjectId(weekly_id),
                            "review": {'$elemMatch': {"manager_id": str(manager_id)},
                        }
                     })
    print(sap)
    if sap is None:                 
        expire_checking = mongo.db.reports.find_one({
            "_id": ObjectId(weekly_id),
            "type": "weekly",
            "user": {
                "$in": juniors
            },
            "is_reviewed": {'$elemMatch': {"_id": manager_id,"expire_id":expire_id}},
            }, { "is_reviewed": 1,"_id": 0 })
        #checking expire time link is valid or not by 15 min time validation
        if expire_checking is not None:
            print("66")
            managers_matching = expire_checking['is_reviewed']
            for manager_matching in managers_matching:
                manager_detail = manager_matching['_id']
                if manager_detail == manager_id:
                    expire_time = manager_matching['expire_time']
            
            if expire_time > datetime.datetime.now():
                print("744444444444444444444444444")
                dab = mongo.db.reports.find({
                    "_id": ObjectId(weekly_id),
                    "type": "weekly",
                    "is_reviewed": {'$elemMatch': {"_id": manager_id}},
                    "user": {
                        "$in": juniors
                    }
                }).sort("created_at", 1)
                dab = [checkin_data(serialize_doc(doc)) for doc in dab]
                print(dab)
                for data in dab:
                    ID = data['user']
                    rap = mongo.db.users.find({
                        "_id": ObjectId(str(ID))
                    })
                    rap = [serialize_doc(doc) for doc in rap]
                    for dub in rap:
                        junior_name = dub['username']
                        slack = dub['slack_id']
                        email = dub['work_email']
                        manager = dub['managers']
                        for a in manager:
                            if a['_id']==str(manager_id):
                                print("97777777777777777777777777")
                                manager_weights=a['weight']
                                manager_name = a['username']
                                ret = mongo.db.reports.update({
                                    "_id": ObjectId(weekly_id)
                                }, {
                                    "$pull": {
                                        "review": {
                                            "manager_id": str(manager_id)
                                        }
                                    }
                                })
                                #updating manager review in report
                                ret = mongo.db.reports.update({
                                    "_id": ObjectId(weekly_id)
                                }, {
                                    "$push": {
                                        "review": {
                                            "rating": rating,
                                            "created_at": datetime.datetime.utcnow(),
                                            "comment": comment,
                                            "manager_id": str(manager_id),
                                            "manager_weight":manager_weights
                                        }
                                    }
                                })
                                
                                cron = mongo.db.reports.update({
                                    "_id": ObjectId(weekly_id)
                                    }, {
                                    "$set": {
                                        "cron_checkin": True
                                    }})
                                #updating report review status true
                                docs = mongo.db.reports.update({
                                    "_id": ObjectId(weekly_id),
                                    "is_reviewed": {'$elemMatch': {"_id": str(manager_id), "reviewed": False}},
                                }, {
                                    "$set": {
                                        "is_reviewed.$.reviewed": True,
                                        "is_reviewed.$.is_notify": True
                                    }})                 
                                state = mongo.db.schdulers_setting.find_one({
                                        "easyRating": {"$exists": True}
                                        }, {"easyRating": 1,'_id': 0})
                                status = state['easyRating']
                                if status == 1:
                                    if rating == 3:
                                        value = "Bad"
                                    if rating == 5:
                                        value = "Neutral"
                                    if rating == 8:
                                        value = "Good"
                                    #sending notification to junior       
                                    user = json.loads(json.dumps(dub,default=json_util.default))
                                    weekly_reviewed_payload = {"user":user,"data":{"manager":manager_name,"rating":str(value),"comment":comment},
                                    "message_key":"weekly_reviewed_notification","message_type":"simple_message"}
                                    notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname,json=weekly_reviewed_payload)
                                    print(notification_message.text)
                                    expires = datetime.timedelta(minutes=5)
                                    access_token = create_access_token(identity=manager_name, expires_delta=expires)
                                    return "Report reviewed successfully.  <a href="+weekly_page_link+"&token="+access_token+">Add comment</a>"
                                else:
                                    user = json.loads(json.dumps(dub,default=json_util.default))
                                    weekly_reviewed_payload = {"user":user,"data":{"manager":manager_name,"rating":str(rating),"comment":comment},
                                    "message_key":"weekly_reviewed_notification","message_type":"simple_message"}
                                    notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname,json=weekly_reviewed_payload)
                                    print(notification_message.text)
                                    print(notification_message.text)
                                    expires = datetime.timedelta(minutes=5)
                                    access_token = create_access_token(identity=manager_name, expires_delta=expires)
                                    return "Report reviewed successfully.  <a href="+weekly_page_link+"&token="+access_token+">Add comment</a>"
            #If link is expired then sending new genrated link.
            else:
                manager_profile = mongo.db.users.find_one({
                    "_id": ObjectId(str(manager_id))
                        })
                manager_profile["_id"] = str(manager_profile["_id"])
                actions = button['actions']
                easy_action = easy_actions['actions']
                new_u_id = str(uuid.uuid4())
                dab = mongo.db.reports.find_one({
                    "_id": ObjectId(weekly_id),
                    "type": "weekly"
                     })                
                if dab is not None:
                    weekly_id = str(dab['_id'])
                    k_highlight = dab['k_highlight']
                    extra = dab['extra']
                    junior_id = dab['user']
                    descriptio = k_highlight[0]
                    description = descriptio['description']
                    user_details = mongo.db.users.find_one({"_id":ObjectId(junior_id)},{"_id":0,"username":1})
                    print(user_details)
                    if user_details is not None:
                        username = user_details['username']
                    else:
                        username ="NA"
                    #updating new 15 min time link validation time and new unique id 
                    docs = mongo.db.reports.update({
                        "_id": ObjectId(weekly_id),
                        "is_reviewed": {'$elemMatch': {"_id": str(manager_id)}},
                            }, {
                        "$set": {
                            "is_reviewed.$.expire_time":datetime.datetime.now() + datetime.timedelta(minutes=15),
                            "is_reviewed.$.expire_id":new_u_id
                        }})
                    state = mongo.db.schdulers_setting.find_one({
                        "easyRating": {"$exists": True}
                        }, {"easyRating": 1,'_id': 0})
                    status = state['easyRating']
                    if status == 1:
                        for action in easy_action:
                            value = action['text']
                            if value == "Bad":
                                rating = "3"
                            if value == "Neutral":
                                rating = "5"
                            if value == "Good":
                                rating = "8"
                            api_url = ""+tms_system_url+"slack_report_review?rating="+str(rating)+"&comment="+comment+"&weekly_id="+str(weekly_id)+"&manager_id="+str(manager_id)+"&unique_id="+str(new_u_id)+""
                            action["url"] = api_url
                        user = json.loads(json.dumps(manager_profile,default=json_util.default))
                        extra_with_msg = (extra +"\nYou can review weekly reports directly from slack now! Just select the rating below.")
                        weekly_payload = {"user":user,
                        "data":{"junior":username, "report":description , "extra":extra_with_msg},"message_key":"expire_weekly_notification","message_type":"button_message","button":easy_actions}
                        notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname,json=weekly_payload)
                        return "your link expired.check your slackbot we just sent you new link for same report"
                    else:
                        for action in actions:
                            rating = action['text']
                            api_url = ""+tms_system_url+"slack_report_review?rating="+str(rating)+"&comment="+comment+"&weekly_id="+str(weekly_id)+"&manager_id="+str(manager_id)+"&unique_id="+str(new_u_id)+""
                            action["url"] = api_url
                        user = json.loads(json.dumps(manager_profile,default=json_util.default))
                        extra_with_msg = (extra +"\nYou can review weekly reports directly from slack now! Just select the rating below.")
                        weekly_payload = {"user":user,
                        "data":{"junior":username, "report":description , "extra":extra_with_msg},"message_key":"expire_weekly_notification","message_type":"button_message","button":button}
                        notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname,json=weekly_payload)
                        return "your link expired.check your slackbot we just sent you new link for same report"
        return "Not a valid link"                                
    return "Report already reviewed"



def checkin_data(weekly_report):
    select_days = weekly_report["select_days"]
    typ = type(select_days)
    if typ==str:
        select_days = [select_days]
    else: 
        select_days = select_days
    
    if select_days is None:
        select_days = None
    else:
        select_days = [load_checkin(day) for day in select_days]
    all_chekin = weekly_report['user']
    all_chekin = (load_all_checkin(all_chekin))
    weekly_report["select_days"] = select_days
    weekly_report['all_chekin'] = all_chekin
    return weekly_report




@bp.route('/checkin', methods=["POST"])
@jwt_required
def add_checkin():
    if not request.json:
        abort(500)

    report = request.json.get("report", None)
    slackReport = request.json.get("slackReport", None)
    task_completed = request.json.get("task_completed", False)
    task_not_completed_reason = request.json.get(
        "task_not_completed_reason", "")
    highlight = request.json.get("highlight", "")
    # date = request.json.get("date", "")
    date = request.json.get("date", None)
    highlight_task_reason = request.json.get("highlight_task_reason", None)
    today = datetime.datetime.utcnow()
    slackChannels = request.json.get("slackChannels", [])

    if not report:
          return jsonify({"msg": "Invalid Request"}), 400

    if task_completed == 1:
        task_completed = True
    else:
        task_completed = False

    current_user = get_current_user()
    username = current_user['username']
    slack = current_user['slack_id']
    if date is None:
        date_time = datetime.datetime.utcnow()
        formatted_date = date_time.strftime("%d-%B-%Y")
        rep = mongo.db.reports.find_one({
            "user": str(current_user["_id"]),
            "type": "daily",
            "created_at": {
                "$gte": datetime.datetime(today.year, today.month, today.day)
            }
        })
        if rep is not None:
            ret = mongo.db.reports.update({
                "user": str(current_user["_id"]),
                "type": "daily",
                "created_at": {
                    "$gte": datetime.datetime(today.year, today.month, today.day)
                }
            }, {
                "$set": {
                    "report": report,
                    "task_completed": task_completed,
                    "task_not_completed_reason": task_not_completed_reason,
                    "highlight": highlight,
                    "highlight_task_reason": highlight_task_reason,
                    "user": str(current_user["_id"]),
                    "created_at": date_time,
                    "username": current_user['username'],
                    "type": "daily"
                }})
            current_user["_id"] = str(current_user["_id"])
            user = json.loads(json.dumps(current_user,default=json_util.default))
            if len(highlight) > 0:
                data = "Report: " + "\n" +slackReport + "" + "\n" + "Highlight: " + highlight
                check_in_payload = {
                    "user": user,
                        "data": data,
                        "slack_channel":slackChannels,
                        "message_type" : "simple_message",
                        "message_key": "check-in"
                    
                }
                notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname, json=check_in_payload)
                print("NEECHE RESPONSE H")
                print(notification_message.text)
            else:
                data = "Report: " + "\n" +slackReport
                check_in_payload = {
                    "user": user,
                        "data": data,
                        "slack_channel":slackChannels,
                        "message_type" : "simple_message",
                        "message_key": "check-in"
                    
                }
                notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname, json=check_in_payload)
                print("NEECHE RESPONSE H")
                print(notification_message.text)
        else:
            ret = mongo.db.reports.insert_one({
                "report": report,
                "task_completed": task_completed,
                "task_not_completed_reason": task_not_completed_reason,
                "highlight": highlight,
                "highlight_task_reason": highlight_task_reason,
                "user": str(current_user["_id"]),
                "created_at": date_time,
                "username": current_user['username'],
                "type": "daily"
            }).inserted_id

            docs = mongo.db.recent_activity.update({
                "user": str(current_user["_id"])},
                {"$push": {"Daily_checkin": {
                    "created_at": date_time,
                    "priority": 0,
                    "Daily_chechkin_message": date_time
                }}}, upsert=True)
            current_user["_id"] = str(current_user["_id"])
            user = json.loads(json.dumps(current_user,default=json_util.default))
            print(user)
            check_in_notification_payload = {
                    "user": user,
                        "data":None,
                        "message_type" : "simple_message",
                        "message_key": "check-in_notification"
                    }
            notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname, json=check_in_notification_payload)
            print("NEECHE RESPONSE H")
            print(check_in_notification_payload)
            print(notification_message.text)
            if len(highlight) > 0:
                data = "Report: " + "\n" +slackReport + "" + "\n" + "Highlight: " + highlight
                check_in_payload = {
                    "user": user,
                    "slack_channel":slackChannels,
                        "data": data,
                        "message_type" : "simple_message",
                        "message_key": "check-in"
                
                }
                notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname, json=check_in_payload)
                print("NEECHE RESPONSE H")
                print(notification_message.text)
            else:
                data = "Report: " + "\n" +slackReport
                check_in_payload = {
                    "user": user,
                        "data": data,
                        "slack_channel":slackChannels,
                        "message_type" : "simple_message",
                        "message_key": "check-in"    
                }
                notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname, json=check_in_payload)
                print("NEECHE RESPONSE H")
                print(notification_message.text)
        return jsonify(str(ret))
    else:
        date_time = datetime.datetime.strptime(date, "%Y-%m-%d")
        sap = mongo.db.reports.insert_one({
            "report": report,
            "task_completed": task_completed,
            "task_not_completed_reason": task_not_completed_reason,
            "highlight": highlight,
            "highlight_task_reason": highlight_task_reason,
            "user": str(current_user["_id"]),
            "created_at": date_time,
            "username": current_user['username'],
            "type": "daily"
        }).inserted_id
        users = mongo.db.users.update({
            "_id": ObjectId(str(current_user['_id']))},
            {"$pull": {"missed_checkin_dates": {
                "date": date,
            }}})
        docs = mongo.db.recent_activity.update({
            "user": str(current_user["_id"])},
            {"$push": {"Daily_checkin": {
                "created_at": datetime.datetime.utcnow(),
                "priority": 0,
                "Daily_chechkin_message": date_time
            }}}, upsert=True)

        return jsonify(str(sap))



@bp.route('/reports', methods=["GET"])
@jwt_required
def checkin_reports():
    current_user = get_current_user()
    today = datetime.datetime.utcnow()
    last_monday = today - datetime.timedelta(days=today.weekday())
    docs = mongo.db.reports.find({
        "user": str(current_user["_id"]),
        "type": "daily",
        "created_at": {
            "$gte": datetime.datetime(last_monday.year, last_monday.month, last_monday.day)
        }
    }).sort("created_at", 1)
    docs = [serialize_doc(doc) for doc in docs]
    return jsonify(docs), 200


@bp.route('/delete/<string:checkin_id>', methods=['DELETE'])
@jwt_required
def delete_checkkin(checkin_id):
    current_user = get_current_user()
    docs = mongo.db.reports.remove({
        "_id": ObjectId(checkin_id),
        "type": "daily",
        "user": str(current_user['_id'])
    })
    return jsonify(str(docs))


@bp.route('/week_checkin', methods=["GET"])
@jwt_required
def week_checkin_reports():
    today = datetime.datetime.today()
    last_sunday = today - datetime.timedelta(days=(today.weekday() + 1))
    last_monday = today - datetime.timedelta(days=(today.weekday() + 8))
    current_user = get_current_user()
    docs = mongo.db.reports.find({
        "user": str(current_user["_id"]),
        "type": "daily",
        "created_at": {
            "$gte": datetime.datetime(last_monday.year, last_monday.month, last_monday.day),
            "$lte": datetime.datetime(last_sunday.year, last_sunday.month, last_sunday.day)
        }
    }).sort("created_at", 1)
    docs = [serialize_doc(doc) for doc in docs]
    return jsonify(docs), 200

    
@bp.route('/revoke_checkin', methods=["GET"])
@jwt_required
def revoke_checkin_reports():
    current_user = get_current_user()
    date_t=current_user["revoke"]
    today = date_t
    last_sunday = today - datetime.timedelta(days=(today.weekday() + 1))
    last_monday = today - datetime.timedelta(days=(today.weekday() + 8))
    current_user = get_current_user()
    docs = mongo.db.reports.find({
        "user": str(current_user["_id"]),
        "type": "daily",
        "created_at": {
            "$gte": datetime.datetime(last_monday.year, last_monday.month, last_monday.day),
            "$lte": datetime.datetime(last_sunday.year, last_sunday.month, last_sunday.day)
        }
    }).sort("created_at", 1)
    docs = [serialize_doc(doc) for doc in docs]
    return jsonify(docs), 200


@bp.route('/weekly_revoked/<string:weekly_id>', methods=["PUT"])
@jwt_required
def delete_weekly_checkin(weekly_id):
    created = request.json.get("created_at", None)
    user = request.json.get("user", None)
    datee=dateutil.parser.parse(created)
    use = mongo.db.users.update({
        "_id": ObjectId(user)},
        {"$set":{
            "revoke":datee
        }
    },upsert=True)

    docs = mongo.db.reports.remove({
        "_id": ObjectId(weekly_id),
        "type": "weekly",
    })
    return jsonify(str(docs))



@bp.route('/week_reports', methods=["GET"])
@jwt_required
def get_week_reports():
    current_user = get_current_user()
    today = datetime.date.today()
    last_sunday = today - datetime.timedelta(days=(today.weekday() + 1))
    last_monday = today - datetime.timedelta(days=(today.weekday() + 8))

    docs = mongo.db.reports.find({
        "user": str(current_user["_id"]),
        "type": "weekly",
        "created_at": {
            "$gte": datetime.datetime(last_monday.year, last_monday.month, last_monday.day),
            "$lte": datetime.datetime(last_sunday.year, last_sunday.month, last_sunday.day)
        }
    }).sort("created_at", 1)
    docs = [serialize_doc(doc) for doc in docs]
    return jsonify(docs), 200



@bp.route('/weekly', methods=["POST", "GET"])
@jwt_required
def add_weekly_checkin():
    current_user = get_current_user()
    today = datetime.datetime.utcnow()
    formated_date = today.strftime("%d-%B-%Y")
    last_monday = today - datetime.timedelta(days=today.weekday())
    if request.method == "GET":
        docs = mongo.db.reports.find({
            "type": "weekly",
            "user": str(current_user["_id"]),
            "created_at": {
                "$gte": datetime.datetime(last_monday.year, last_monday.month, last_monday.day)}
        }).sort("created_at", 1)
        docs = [serialize_doc(doc) for doc in docs]
        return jsonify(docs), 200
    if not request.json:
        abort(500)

    k_highlight = request.json.get("k_highlight", None)
    extra = request.json.get("extra","")
    select_days = request.json.get("select_days", [])
    difficulty = request.json.get("difficulty", 0)
    username = current_user['username']
    slack = current_user['slack_id']
 
    if not k_highlight and select_days:
        return jsonify({"msg": "Invalid Request"}), 400
    
    docs = mongo.db.reports.find({
            "type": "daily",
            "user": str(current_user["_id"]),
            "created_at": {
                "$gte": datetime.datetime(last_monday.year, last_monday.month, last_monday.day)}
        }).sort("created_at", 1)
    print(docs)
    docs = [serialize_doc(doc) for doc in docs]
    report = []
    for doc in docs:
        report.append(doc['report'])


    reviewed = False
    users = mongo.db.users.find({
        "_id": ObjectId(current_user["_id"])
    })
    users = [serialize_doc(doc) for doc in users]

    managers_data = []
    for data in users:
        print("jkdsfjksd" ,data)
        for mData in data['managers']:
            mData['reviewed'] = reviewed
            mData['expire_time'] = datetime.datetime.now() + datetime.timedelta(minutes=15)
            mData['expire_id'] = str(uuid.uuid4())
            mData['is_notify']= False
            managers_data.append(mData)

    if 'kpi_id' in users:
        kpi_doc = mongo.db.kpi.find_one({
            "_id": ObjectId(current_user['kpi_id'])
        })
        kpi_name = kpi_doc['kpi_json']
        era_name = kpi_doc['era_json']
    else:
        kpi_name = ""
        era_name = ""
        
    managers_name = []
    for elem in managers_data:
        managers_name.append({"Id":elem['_id'],"unique_id":elem['expire_id']})    
    
    ret = mongo.db.reports.insert_one({
        "k_highlight": k_highlight,
        "report": report,
        "extra": extra,
        "select_days": select_days,
        "user": str(current_user["_id"]),
        "created_at": datetime.datetime.utcnow(),
        "type": "weekly",
        "is_reviewed": managers_data,
        "cron_checkin": True,
        "cron_review_activity": False,
        "kpi_json": kpi_name,
        "era_json": era_name,
        "difficulty": difficulty
    }).inserted_id
    descriptio = k_highlight[0]
    # print("sdfshds",k_highlight)
    description = descriptio['description']
    # description = k_highlight
    for element in managers_name:
        manager = element['Id']
        rec = mongo.db.recent_activity.update({
            "user": manager},
            {"$push": {
                "Junior_weekly": {
                    "created_at": datetime.datetime.now(),
                    "priority": 1,
                    "Message": str(username)+' '+"have created a weekly report please review it"
                }}}, upsert=True)

    weekly_id = str(ret)
    state = mongo.db.schdulers_setting.find_one({
        "easyRating": {"$exists": True}
        }, {"easyRating": 1,'_id': 0})
    
    status = state['easyRating']
    for manger_id in managers_name:
        mang_id = manger_id['Id']
        unique_id = manger_id['unique_id']
        manager_profile = mongo.db.users.find_one({
            "_id": ObjectId(str(mang_id))
                })
        manager_profile["_id"] = str(manager_profile["_id"])
        actions = button['actions']
        easy_action = easy_actions['actions']
        print(status)
        if status == 1:
            for action in easy_action:
                value = action['text']
                if value == "Bad":
                    rating = "3"
                if value == "Neutral":
                    rating = "5"
                if value == "Good":
                    rating = "8"
                api_url = ""+tms_system_url+"slack_report_review?rating="+rating+"&comment=""&weekly_id="+weekly_id+"&manager_id="+mang_id+"&unique_id="+unique_id+""
                action["url"] = api_url
            user = json.loads(json.dumps(manager_profile,default=json_util.default))
            extra_with_msg = (extra +"\nYou can review weekly reports directly from slack now! Just select the rating below.")
            weekly_payload = {"user":user,
            "data":{"junior":username, "report":description , "extra":extra_with_msg},"message_key":"weekly_notification","message_type":"button_message","button":easy_actions}
            notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname,json=weekly_payload)        
        else:
            for action in actions:
                rating = action['text']
                api_url = ""+tms_system_url+"slack_report_review?rating="+rating+"&comment=""&weekly_id="+weekly_id+"&manager_id="+mang_id+"&unique_id="+unique_id+""
                action["url"] = api_url
            user = json.loads(json.dumps(manager_profile,default=json_util.default))
            extra_with_msg = (extra +"\nYou can review weekly reports directly from slack now! Just select the rating below.")
            weekly_payload = {"user":user,
            "data":{"junior":username, "report":description , "extra":extra_with_msg},"message_key":"weekly_notification","message_type":"button_message","button":button}
            # notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname,json=weekly_payload)
    return jsonify(str(ret)), 200


@bp.route('/weekly_automated', methods=["POST"])
@jwt_required
def add_weekly_automated():
    current_user = get_current_user()
    today = datetime.datetime.utcnow()
    slack = current_user['slack_id']
    formated_date = today.strftime("%d-%B-%Y")
    last_monday = today - datetime.timedelta(days=today.weekday())
    username = current_user['username']
    state = mongo.db.schdulers_setting.find_one({
        "weekly_automated": {"$exists": True}
        }, {"weekly_automated": 1, '_id': 0})
    status = state['weekly_automated']
    if status == 1:
        docs = mongo.db.reports.find_one({
                "type": "weekly",
                "user": str(current_user["_id"]),
                "created_at": {
                    "$gte": datetime.datetime(last_monday.year, last_monday.month, last_monday.day)}
            })

        if not docs:
            reviewed = False
            users = mongo.db.users.find({
                "_id": ObjectId(current_user["_id"])
            })
            users = [serialize_doc(doc) for doc in users]
            managers_data = []
            for data in users:
                for mData in data['managers']:
                    mData['reviewed'] = reviewed
                    mData['expire_time'] = datetime.datetime.now() + datetime.timedelta(minutes=15)
                    mData['expire_id'] = str(uuid.uuid4())
                    mData['is_notify'] = False
                    managers_data.append(mData)

            if 'kpi_id' in users:
                kpi_doc = mongo.db.kpi.find_one({
                    "_id": ObjectId(current_user['kpi_id'])
                })
                kpi_name = kpi_doc['kpi_json']
                era_name = kpi_doc['era_json']
            else:
                kpi_name = ""
                era_name = ""
                
            managers_name = []
            for elem in managers_data:
                managers_name.append({"Id":elem['_id'],"unique_id":elem['expire_id']})
            
            last_monday = today - datetime.timedelta(days=(today.weekday() + 8))
            last_sunday = today - datetime.timedelta(days=(today.weekday() + 1))
            ret = mongo.db.reports.find_one({
                "user": str(current_user["_id"]),
                "type": "daily",
                "created_at": {
                    "$gte": datetime.datetime(last_monday.year, last_monday.month, last_monday.day),
                    "$lte": datetime.datetime(last_sunday.year, last_sunday.month, last_sunday.day)}
            })
            if ret:
                select_days = ret['_id']
                ret = mongo.db.reports.insert_one({
                    "k_highlight": [{"KpiEra": "NA", "description": "NA"}],
                    "extra": "NA",
                    "select_days":[str(select_days)],
                    "user": str(current_user["_id"]),
                    "created_at": datetime.datetime.utcnow(),
                    "type": "weekly",
                    "is_reviewed": managers_data,
                    "cron_checkin": True,
                    "cron_review_activity": False,      
                    "kpi_json": kpi_name,
                    "era_json": era_name,
                    "difficulty": 0
                }).inserted_id
                
                weekly_id = str(ret)
                
                for manger_id in managers_name:
                    mang_id = manger_id['Id']
                    unique_id = manger_id['unique_id']
                    manager_profile = mongo.db.users.find_one({
                        "_id": ObjectId(str(mang_id))
                            })
                    manager_profile["_id"] = str(manager_profile["_id"])
                    actions = button['actions']
                    for action in actions:
                        rating = action['text']
                        api_url = ""+tms_system_url+"slack_report_review?rating="+rating+"&comment=""&weekly_id="+weekly_id+"&manager_id="+mang_id+"&unique_id="+unique_id+""
                        action["url"] = api_url
                    user = json.loads(json.dumps(manager_profile,default=json_util.default))
                    extra = "NA"
                    extra_with_msg = (extra +"\nYou can review weekly reports directly from slack now! Just select the rating below.")
                    weekly_payload = {"user":user,
                    "data":{"junior":username, "report":"This is lazy weekly submit by your junior" , "extra":extra_with_msg},"message_key":"weekly_notification","message_type":"button_message","button":button}
                    notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname,json=weekly_payload)
                    return jsonify({"msg":"weekly report has been successfully submitted"}), 200
            else:
                return jsonify({"msg": "you don't have daily checkin to submit"}),403
        else:
            return jsonify({"msg": "You have already submitted weekly checkin for this week"}),403
    else:
        return jsonify({"msg": "This feature has been turned off by Admin"}),403


@bp.route('/delete_weekly/<string:weekly_id>', methods=['DELETE'])
@jwt_required
def delete_weekly(weekly_id):
    current_user = get_current_user()
    docs = mongo.db.reports.remove({
        "_id": ObjectId(weekly_id),
        "type": "weekly",
        "user": str(current_user['_id'])
    })
    return jsonify(str(docs))

def load_checkin(id):
    print("load checkin id")
    print(id)
    ret = mongo.db.reports.find_one({
        "_id": ObjectId(id)
    })
    if not ret:
        sap = mongo.db.archive_report.find_one({
            "_id": id
        })
        return serialize_doc(sap)
    else:
        return serialize_doc(ret)


def load_all_checkin(all_chekin):
    today = datetime.datetime.utcnow()
    last_monday = today - datetime.timedelta(days=(today.weekday() + 8))
    last_sunday = today - datetime.timedelta(days=(today.weekday() + 1))
    ret = mongo.db.reports.find({
        "user": all_chekin,
        "type": "daily",
        "created_at": {
            "$gte": datetime.datetime(last_monday.year, last_monday.month, last_monday.day),
            "$lte": datetime.datetime(last_sunday.year, last_sunday.month, last_sunday.day)}
    }).sort("created_at", 1)
    ret = [serialize_doc(doc) for doc in ret]
    return ret


def notes(selectdays):
    for id in selectdays:
        ret = mongo.db.reports.find_one({
        "_id": ObjectId(id)
        })
        if not ret:
            sap = mongo.db.archive_report.find_one({
                "_id": id
            }) 
            user = sap['user']
            today = sap['created_at']
        else:
            user = ret['user']
            today = ret['created_at']
        current_user = get_current_user()
        last_monday = today - datetime.timedelta(days=today.weekday())
        coming_monday = today + datetime.timedelta(days=-today.weekday(), weeks=1)
        print(last_monday)
        print(coming_monday)
        print(user)
        ret = mongo.db.weekly_notes.find({
            "junior_id": user,
            "manager_id": str(current_user['_id']),
            "created_at": {
                "$gte": last_monday,
                "$lt": coming_monday}
        })
        ret = [serialize_doc(doc) for doc in ret]
        return ret



def add_checkin_data(weekly_report):
    print("report whose select_days is to be found")
    print(weekly_report)
    select_days = weekly_report["select_days"]
    typ = type(select_days)
    if typ==str:
        print("lenn")
        select_days = [select_days]
    else: 
        select_days = select_days
    
    print(select_days)
    if select_days is None:
        print("under None loop")
        print("NONE LOOP")
        select_days = None
    else:
        print("ID FOUND LOOP")
        print("id found loop")
        note =(notes(select_days))
        select_days = [load_checkin(day) for day in select_days]
    print("data which is loaded")
    all_chekin = weekly_report['user']
    all_chekin = (load_all_checkin(all_chekin))
    weekly_report["select_days"] = select_days
    weekly_report['all_chekin'] = all_chekin
    weekly_report['note'] = note
    return weekly_report


@bp.route("/manager_weekly_all", methods=["GET"])
@jwt_required
@token.manager_required
def get_manager_weekly_list_all():
    today = datetime.datetime.utcnow()
    last_monday = today - datetime.timedelta(days=today.weekday())
    current_user = get_current_user()
    juniors = get_manager_juniors(current_user['_id'])
    repo=[]
    docss = mongo.db.reports.find({
        "type": "weekly",
        "is_reviewed": {'$elemMatch': {"_id": str(current_user["_id"])}},
        "created_at": {
            "$gte": datetime.datetime(last_monday.year, last_monday.month, last_monday.day),
        },
        "user": {
            "$in": juniors
        }
    }).sort("created_at", 1)
    docss = [add_checkin_data(serialize_doc(doc)) for doc in docss]
    for a in docss:
        repo.append(a)
    docs = mongo.db.reports.find({
        "type": "weekly",
        "is_reviewed": {'$elemMatch': {"_id": str(current_user["_id"]), "reviewed": False}},
        "user": {
            "$in": juniors
        }
    }).sort("created_at", 1)
    docs = [add_checkin_data(serialize_doc(doc)) for doc in docs]
    for b in docs:
        if b not in repo:
            repo.append(b)
    return jsonify(repo), 200


@bp.route("/manager_weekly", methods=["GET"])
@bp.route("/manager_weekly/<string:weekly_id>", methods=["POST"])
@jwt_required
@token.manager_required
def get_manager_weekly_list(weekly_id=None):
    current_user = get_current_user()
    manager_name = current_user['username']
    if request.method == "GET":
        juniors = get_manager_juniors(current_user['_id'])

        docs = mongo.db.reports.find({
            "type": "weekly",
            "is_reviewed": {'$elemMatch': {"_id": str(current_user["_id"]), "reviewed": False}},
            "user": {
                "$in": juniors
            }
        }).sort("created_at", 1)
        docs = [add_checkin_data(serialize_doc(doc)) for doc in docs]
        return jsonify(docs), 200
    else:
        if not request.json:
            abort(500)
        rating = request.json.get("rating", 0)
        comment = request.json.get("comment", None)

        if comment is None or weekly_id is None:
            return jsonify(msg="invalid request"), 500
        juniors = get_manager_juniors(current_user['_id'])
        print(juniors)
        dab = mongo.db.reports.find({
            "_id": ObjectId(weekly_id),
            "type": "weekly",
            "is_reviewed": {'$elemMatch': {"_id": str(current_user["_id"]), "reviewed": False}},
            "user": {
                "$in": juniors
            }
        }).sort("created_at", 1)
        dab = [add_checkin_data(serialize_doc(doc)) for doc in dab]
        print(dab)
        for data in dab:
            ID = data['user']
            print(ID)
            rap = mongo.db.users.find({
                "_id": ObjectId(str(ID))
            })
            rap = [serialize_doc(doc) for doc in rap]
            for dub in rap:
                print(dub)
                junior_name = dub['username']
                slack = dub['slack_id']
                email = dub['work_email']
                print(slack)
                manager = dub['managers']
                for a in manager:
                    print("YHA pE")
                    if a['_id']==str(current_user["_id"]):
                        manager_weights=a['weight']
                        sap = mongo.db.reports.find({
                            "_id": ObjectId(weekly_id),
                            "review": {'$elemMatch': {"manager_id": str(current_user["_id"])},
                        }
                     })
                        sap = [serialize_doc(saps) for saps in sap]
                        if not sap:
                            ret = mongo.db.reports.update({
                                "_id": ObjectId(weekly_id)
                            }, {
                                "$push": {
                                    "review": {
                                        "rating": rating,
                                        "created_at": datetime.datetime.utcnow(),
                                        "comment": comment,
                                        "manager_id": str(current_user["_id"]),
                                        "manager_weight":manager_weights
                                    }
                                }
                            })

                            cron = mongo.db.reports.update({
                                "_id": ObjectId(weekly_id)
                                }, {
                                "$set": {
                                    "cron_checkin": True
                                }})


                            docs = mongo.db.reports.update({
                                "_id": ObjectId(weekly_id),
                                "is_reviewed": {'$elemMatch': {"_id": str(current_user["_id"]), "reviewed": False}},
                            }, {
                                "$set": {
                                    "is_reviewed.$.reviewed": True,
                                    "is_reviewed.$.is_notify": True
                                }},upsert=True)
                            dec = mongo.db.recent_activity.update({
                                "user": str(ID)},
                                {"$push": {
                                    "report_reviewed": {
                                        "created_at": datetime.datetime.now(),
                                        "priority": 0,
                                        "Message": "Your weekly report has been reviewed by "" " + manager_name
                                    }}}, upsert=True)
                            user = json.loads(json.dumps(dub,default=json_util.default))
                            print(user)
                            print("YE MAIN H")
                            print("user",user,"manager",manager_name,"rating",rating,"comment",comment)
                            weekly_reviewed_payload = {"user":user,"data":{"manager":manager_name,"rating":str(rating),"comment":comment},
                            "message_key":"weekly_reviewed_notification","message_type":"simple_message"}
                            notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname,json=weekly_reviewed_payload)
                            print("notification status====>")
                            print(notification_message.text)
                            return jsonify(str(ret)), 200
                        else:
                            return jsonify(msg="Already reviewed this report"), 400



@bp.route("/manager_weekly/update/<string:weekly_id>", methods=["PUT"])
@jwt_required
@token.manager_required
def update_manager_weekly(weekly_id=None):
    current_user = get_current_user()
    if not request.json:
        abort(500)
    rating = request.json.get("rating", 0)
    comment = request.json.get("comment", None)

    if comment is None or weekly_id is None:
        return jsonify(msg="invalid request"), 500

    ret = mongo.db.reports.find_one({
        "_id": ObjectId(weekly_id),
        "review": {'$elemMatch': {"manager_id": str(current_user["_id"])}},
    })
    if ret is not None:
        ret = mongo.db.reports.update({
            "_id": ObjectId(weekly_id),
            "review": {'$elemMatch': {"manager_id": str(current_user["_id"])}},
        }, {
            "$set": {
                "review.$.rating":rating,
                "review.$.updated_at":datetime.datetime.utcnow(),
                "review.$.comment":comment,
                "review.$.manager_id":str(current_user["_id"])
            }
        },upsert=True)
    else:
        juniors = get_manager_juniors(current_user['_id'])
        dab = mongo.db.reports.find({
            "_id": ObjectId(weekly_id),
            "type": "weekly",
            "is_reviewed": {'$elemMatch': {"_id": str(current_user["_id"]), "reviewed": False}},
            "user": {
                "$in": juniors
            }
        }).sort("created_at", 1)
        dab = [add_checkin_data(serialize_doc(doc)) for doc in dab]
        for data in dab:
            ID = data['user']
            rap = mongo.db.users.find({
                "_id": ObjectId(str(ID))
            })
            rap = [serialize_doc(doc) for doc in rap]
            for dub in rap:
                print(dub)
                junior_name = dub['username']
                slack = dub['slack_id']
                email = dub['work_email']
                print(slack)
                manager = dub['managers']
                for a in manager:
                    print("YHA pE")
                    if a['_id']==str(current_user["_id"]):
                        manager_weights=a['weight']
                        sap = mongo.db.reports.find({
                            "_id": ObjectId(weekly_id),
                            "review": {'$elemMatch': {"manager_id": str(current_user["_id"])},
                        }
                        })
                        sap = [serialize_doc(saps) for saps in sap]
                        if not sap:
                            ret = mongo.db.reports.update({
                                "_id": ObjectId(weekly_id)
                            }, {
                                "$push": {
                                    "review": {
                                        "rating": rating,
                                        "created_at": datetime.datetime.utcnow(),
                                        "comment": comment,
                                        "manager_id": str(current_user["_id"]),
                                        "manager_weight":manager_weights
                                    }
                                }
                            })

                            cron = mongo.db.reports.update({
                                "_id": ObjectId(weekly_id)
                                }, {
                                "$set": {
                                    "cron_checkin": True
                                }})


                            docs = mongo.db.reports.update({
                                "_id": ObjectId(weekly_id),
                                "is_reviewed": {'$elemMatch': {"_id": str(current_user["_id"]), "reviewed": False}},
                            }, {
                                "$set": {
                                    "is_reviewed.$.reviewed": True,
                                    "is_reviewed.$.is_notify": True
                                }},upsert=True)
    return jsonify({"status":"success"}), 200




@bp.route('/week_reviewed_reports', methods=["GET"])
@jwt_required
def week_reviewed_reports():
    current_user = get_current_user()
    today = datetime.date.today()
    last_sunday = today - datetime.timedelta(days=(today.weekday() + 1))
    last_monday = today - datetime.timedelta(days=(today.weekday() + 8))

    docs = mongo.db.reports.find({
        "user": str(current_user["_id"]),
        "type": "weekly",
        "review": {"$exists": True},
        "created_at": {
            "$gte": datetime.datetime(last_monday.year, last_monday.month, last_monday.day)
            
        }
    }).sort("created_at", 1)
    docs = [add_checkin_data(serialize_doc(doc)) for doc in docs]
    return jsonify(docs), 200



    
@bp.route('/recent_activities', methods=['GET'])
@jwt_required
def recent_activity():
    current_user = get_current_user()
    ret = mongo.db.recent_activity.find({
        "user": str(current_user['_id'])
    })
    ret = [serialize_doc(ret) for ret in ret]
    return jsonify(ret)

def load_kpi(kpi_data):
    print(kpi_data)
    ret = mongo.db.kpi.find_one({
        "_id": ObjectId(kpi_data)
    })
    return serialize_doc(ret)


def add_kpi_data(kpi):
    if "kpi_id" in kpi:
        data = kpi["kpi_id"]
        kpi_data = (load_kpi(data))
        kpi['kpi_id'] = kpi_data
    else:
        kpi['kpi_id'] = ""
    return kpi


@bp.route('/managers_juniors', methods=['GET'])
@jwt_required
@token.manager_required
def manager_junior():
    current_user = get_current_user()
    users = mongo.db.users.find({
        "managers": {
            "$elemMatch": {"_id": str(current_user['_id'])}
           
        }, "status": "Enabled"
    }).sort("created_at", 1)
    users = [add_kpi_data(serialize_doc(ret)) for ret in users]
    return jsonify(users)


def load_user(user):
    ret = mongo.db.users.find_one({
        "_id": ObjectId(user)
    })
    return serialize_doc(ret)


def add_user_data(user):
    user_data = user['user']
    user_data = (load_user(user_data))
    user['user'] = user_data
    return user


@bp.route('/juniors_chechkin', methods=['GET'])
@jwt_required
@token.manager_required
def junior_chechkin():
    current_user = get_current_user()
    users = mongo.db.users.find({
        "managers": {
            "$elemMatch": {"_id": str(current_user['_id'])}
        }
    })
    users = [serialize_doc(ret) for ret in users]
    ID = []
    for data in users:
        ID.append(data['_id'])
    print(ID)
    reports = mongo.db.reports.find({
        "user": {"$in": ID},
        "type": "daily"
    }).sort("created_at", 1)
    reports = [add_user_data(serialize_doc(doc)) for doc in reports]
    return jsonify(reports)


def load_manager(manager):
    ret = mongo.db.users.find_one({
        "_id": manager
    })
    return serialize_doc(ret)


def add_manager_data(manager):
    for elem in manager['review']:
        elem['manager_id'] = load_manager(ObjectId(elem['manager_id']))
    return manager


#Api for juniours see manager review.
@bp.route('/junior_review_response', methods=["GET"])
@jwt_required
def junior_review_response():
   current_user = get_current_user()
   docs = mongo.db.reports.find({
       "user": str(current_user["_id"]),
       "type": "weekly",
       "review": {'$exists': True},
   }).sort("created_at", 1)
   docs = [add_manager_data(serialize_doc(doc)) for doc in docs]
   return jsonify(docs)


@bp.route('/employee_feedback', methods=['POST', 'GET'])
@jwt_required
def employee_feedback():
    today = datetime.datetime.utcnow()
    month = today.strftime("%B")
    current_user = get_current_user()
    user = str(current_user['_id'])
    if request.method == "GET":
        rep = mongo.db.reports.find({
            "user": user,
            "type": "feedback",
        })
        rep = [add_user_data(serialize_doc(doc)) for doc in rep]
        return jsonify(rep), 200
    else:
        if not request.json:
            abort(500)
        feedback = request.json.get("feedback", "")
        rep = mongo.db.reports.find_one({
            "user": user,
            "type": "feedback",
            "month": month,
        })
        if rep is not None:
            return jsonify({"msg": "You have already submitted feedback for this month"}), 409
        else:
            report = mongo.db.reports.insert_one({
                "feedback": feedback,
                "user": user,
                "month": month,
                "type": "feedback",
            }).inserted_id
            return jsonify(str(report)), 200


@bp.route('/admin_fb_reply', methods=['GET'])
@bp.route('/admin_fb_reply/<string:feedback_id>', methods=['POST'])
@jwt_required
@token.admin_required
def admin_reply(feedback_id=None):
    current_user = get_current_user()
    username = current_user['username']
    if 'profileImage' in current_user:
        profileImage = current_user['profileImage']
    else:
        profileImage = ""
    if request.method == "GET":
        rep = mongo.db.reports.find({
            "type": "feedback"
        })
        rep = [add_user_data(serialize_doc(ret)) for ret in rep]
        return jsonify(rep), 200
    else:
        if not request.json:
            abort(500)
        reply = request.json.get("reply", None)
        report = mongo.db.reports.update({
            "_id": ObjectId(feedback_id),
            "type": "feedback"
        }, {
            "$set": {
                "admin_response": {
                "Reply": reply,
                "username": username,
                "profileImage": profileImage
                }
            }
        })
        return jsonify(str(report)), 200

def load_details(data):
    user_data = data['user']
    user_data = (load_user(user_data))
    data['user'] = user_data
    if 'review' in data:
        review_detail = data['review']
    else:
        review_detail = None
    if review_detail is not None:
        for elem in review_detail:
            elem['manager_id'] = load_manager(ObjectId(elem['manager_id']))
    return data

def no_review(data):
    user_data = data['user']
    user_data = (load_user(user_data))
    data['user'] = user_data
    review_data = None
    data['review'] = review_data
    return data


@bp.route('/junior_weekly_report', methods=['GET'])
@jwt_required
@token.manager_required
def junior_weekly_report():
    current_user = get_current_user()
    users = mongo.db.users.find({
        "managers": {
            "$elemMatch": {"_id": str(current_user['_id'])}
        }
    })
    users = [serialize_doc(ret) for ret in users]
    ID = []
    for data in users:
        ID.append(data['_id'])
    print(ID)
    reports = mongo.db.reports.find({
        "user": {"$in": ID},
        "type": "weekly",
        "is_reviewed": {'$elemMatch': {"_id": str(current_user["_id"]), "reviewed": False}}
    }).sort("created_at", 1)
    reports = [no_review(serialize_doc(doc)) for doc in reports]
    report = mongo.db.reports.find({
        "user": {"$in": ID},
        "type": "weekly",
        "is_reviewed": {'$elemMatch': {"_id": str(current_user["_id"]), "reviewed": True}}
    }).sort("created_at", 1)
    report = [load_details(serialize_doc(doc)) for doc in report]
    report_all = reports + report

    return jsonify(report_all)


@bp.route('/delete_manager_response/<string:weekly_id>', methods=['DELETE'])
@jwt_required
@token.manager_required
def delete_manager_response(weekly_id):
    current_user = get_current_user()
    today = datetime.datetime.utcnow()
    last_day = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
    next_day = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    report = mongo.db.reports.find_one({
        "_id": ObjectId(weekly_id),
        "review": {'$elemMatch': {"manager_id": str(current_user["_id"]), "created_at": {
                    "$gte": last_day,
                    "$lte": next_day}}
        }})
    print(report)
    if report is not None:
        ret = mongo.db.reports.update({
            "_id": ObjectId(weekly_id)}
            , {
            "$pull": {
                "review": {
                    "manager_id": str(current_user["_id"]),
                    }
            }})
        docs = mongo.db.reports.update({
            "_id": ObjectId(weekly_id),
            "is_reviewed": {'$elemMatch': {"_id": str(current_user["_id"]), "reviewed": True}},
        }, {
            "$set": {
                "is_reviewed.$.reviewed": False
            }})
        return jsonify(str(docs)), 200
    else:
        return jsonify({"msg": "You can no longer delete your submitted report"}), 400




@bp.route('/skip_review/<string:weekly_id>', methods=['POST'])
@jwt_required
@token.manager_required
def skip_review(weekly_id):
    state = mongo.db.schdulers_setting.find_one({
        "skip_review": {"$exists": True},
        "only_manager_skip": {"$exists": True}
    }, {"skip_review": 1,"only_manager_skip":1, '_id': 0})
    if state is not None:
        status = state['skip_review']
        only_manager_skip = state['only_manager_skip']
    else:
        status = default_skip_settings['skip_review']
        only_manager_skip = default_skip_settings['only_manager_skip']

    if status == 1:
        current_user = get_current_user()
        # message=load_weekly_notes()
        name = current_user['username']
        #findng current user date of joining.
        doj = current_user['dateofjoining']
        today = datetime.datetime.utcnow()
        month = today.strftime("%B")
        #finding report by report id
        reason = request.json.get("reason",None)
        selected = request.json.get("selected",None)
        reports = mongo.db.reports.find_one({
            "_id": ObjectId(weekly_id),
            "is_reviewed": {'$elemMatch': {"_id": str(current_user["_id"])}
            }
        })
        #finding all managers review status. is manager have done his review or not.
        review_check=[]
        user=reports['user']    
        reviewed_array = reports['is_reviewed']
        for review in reviewed_array:
            review_check.append(review['reviewed'])
        print(user)
        users = mongo.db.users.find({
            "_id": ObjectId(user)
            })

        users = [serialize_doc(doc) for doc in users]
        for user_info in users:
            slack_id = user_info['slack_id']
            junior_name = user_info['username']
        #checking if a single manager have done his review then allow the user to skip his review.
        print("resonnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn")
        print(reason)
        if selected=="b" or selected=="a":
            msg = "Weekly report is skipped by"+ ' '+name
        
        elif selected=="d":
            report = mongo.db.reports.insert_one({
                "feedback": "I am no longer associated in any project with "+ junior_name,
                "user": str(current_user["_id"]),
                "month": month,
                "type": "feedback",
            }).inserted_id
            msg = "Weekly report is skipped by"+ ' '+name
        else:
            msg = "Weekly report is skipped by"+' '+name+' '+"because"+' '+reason
        
        #Checking if only manager can skip condition is true or false
        if only_manager_skip == 1:
            rep = mongo.db.reports.update({
                    "_id": ObjectId(weekly_id)
                    }, {
                    "$push": {
                        "skip_reason":msg }
                    }, upsert=False)
        
            rep = mongo.db.reports.update({
                    "_id": ObjectId(weekly_id),
                    "is_reviewed": {'$elemMatch': {"_id": str(current_user["_id"])}},
                }, {
                    "$pull": {
                        "is_reviewed": {"_id": str(current_user["_id"])}
                    }}, upsert=False)
            user = json.loads(json.dumps(user_info,default=json_util.default))
            weekly_skipped_payload = {"user":user,
            "data":name,"message_key":"weekly_skipped_notification","message_type":"simple_message"}
            notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname,json=weekly_skipped_payload)
            return jsonify({"status":"success"})
        else:
            if 1 in review_check:
                rep = mongo.db.reports.update({
                        "_id": ObjectId(weekly_id)
                        }, {
                        "$push": {
                            "skip_reason":msg }
                        }, upsert=False)
            
                rep = mongo.db.reports.update({
                        "_id": ObjectId(weekly_id),
                        "is_reviewed": {'$elemMatch': {"_id": str(current_user["_id"])}},
                    }, {
                        "$pull": {
                            "is_reviewed": {"_id": str(current_user["_id"])}
                        }}, upsert=False)
                user = json.loads(json.dumps(user_info,default=json_util.default))
                weekly_skipped_payload = {"user":user,
                "data":name,"message_key":"weekly_skipped_notification","message_type":"simple_message"}
                notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname,json=weekly_skipped_payload)
                return jsonify({"status":"success"})
            else:
                #finding all assign managers_id
                manager_id = []
                for elem in reports['is_reviewed']:
                    manager_id.append(ObjectId(elem['_id']))
                #finding all assign managers weights and current_manager weights
                manager_weight = []
                current_manag_weight=[]
                for elem in reports['is_reviewed']:
                    manager_weight.append(elem['weight'])
                    if elem['_id'] == str(current_user["_id"]):
                        current_manag_weight.append(elem['weight'])
                #finding all mangers by id
                managers = mongo.db.users.find({
                    "_id": {"$in": manager_id}
                })
                managers = [serialize_doc(doc) for doc in managers]
                #finding managers join date.
                join_date = []
                for dates in managers:
                    join_date.append(dates['dateofjoining'])
            
                for weig in current_manag_weight:
                    current_m_weight = weig
                no_of_time = manager_weight.count(current_m_weight)
                #checking if two managers have same weights.
                if no_of_time > 1:
                    #checking that assign manager is greater then one or not if a single manager left then he can not skip report
                    if len(join_date) > 1:
                        oldest = min(join_date)
                        if doj == oldest:
                            rep = mongo.db.reports.update({
                            "_id": ObjectId(weekly_id)
                            }, {
                            "$push": {
                                "skip_reason":msg }
                            }, upsert=False)    
                            
                            rep = mongo.db.reports.update({
                                "_id": ObjectId(weekly_id),
                                "is_reviewed": {'$elemMatch': {"_id": str(current_user["_id"])}},
                            }, {
                                "$pull": {
                                    "is_reviewed": {"_id": str(current_user["_id"])}
                                }}, upsert=False)
                            user = json.loads(json.dumps(user_info,default=json_util.default))
                            weekly_skipped_payload = {"user":user,
                            "data":name,"message_key":"weekly_skipped_notification","message_type":"simple_message"}
                            notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname,json=weekly_skipped_payload)
                            return jsonify({"status":"success"})
                        else:
                            return jsonify({"msg": "Senior manager needs to give review before you can skip"}), 400
                    else:
                        return jsonify({"msg": "You cannot skip this report review as you are the only manager"}), 400
                else:
                    #checking that assign manager is greater then one or not if a single manager left then he can not skip report
                    if len(manager_weight)>1:
                        #finding max weight in weight list
                        max_weight = max(manager_weight)
                        #if current manager weight is max then he can skip his review
                        if current_m_weight == max_weight:
                            rep = mongo.db.reports.update({
                            "_id": ObjectId(weekly_id)
                            }, {
                            "$push": {
                                "skip_reason":msg }
                            }, upsert=False)
                            
                            rep = mongo.db.reports.update({
                                "_id": ObjectId(weekly_id),
                                "is_reviewed": {'$elemMatch': {"_id": str(current_user["_id"])}},
                            }, {
                                "$pull": {
                                    "is_reviewed": {"_id": str(current_user["_id"])}
                                }}, upsert=False)
                            user = json.loads(json.dumps(user_info,default=json_util.default))
                            weekly_skipped_payload = {"user":user,
                            "data":name,"message_key":"weekly_skipped_notification","message_type":"simple_message"}
                            notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname,json=weekly_skipped_payload)
                            return jsonify({"status":"success"})
                        else:
                            return jsonify({"msg": "Manager with higher weight needs to give review before you can skip"}), 400
                    else:
                        return jsonify({"msg": "You cannot skip this report review as you are the only manager"}), 400        
    else:
        return jsonify({"msg": "Admin not allow to skip review"}), 400



#Api for add note in weekly
@bp.route('/review_note', methods=['POST'])
@jwt_required
@token.manager_required
def review_note():
    current_user = get_current_user()
    comment = request.json.get("comment",None)
    junior_id = request.json.get("junior_id",None)
    ret = mongo.db.weekly_notes.insert_one({
                "comment":comment,
                "manager_id":str(current_user['_id']),
                "junior_id":junior_id,
                "created_at":datetime.datetime.utcnow(),
                "type":"weekly_note"
            }).inserted_id
    return jsonify({"status":"success"})
                        

#Api for get notes which add on junior report. 
@bp.route('/review_note/get_review', methods=['GET'])
@jwt_required
@token.manager_required
def review_note_get():
    current_user = get_current_user()
    today = datetime.datetime.utcnow()
    last_monday = today - datetime.timedelta(days=today.weekday())
    rev = mongo.db.weekly_notes.find({
        "manager_id":str(current_user["_id"]),
        "created_at": {
                "$gte": datetime.datetime(last_monday.year, last_monday.month, last_monday.day)
                }
        })
    rev = [serialize_doc(doc) for doc in rev]
    return jsonify(rev)



#Api for delete or update notes
@bp.route('/review_note/delete_review/<string:note_id>', methods=['DELETE','PUT'])
@jwt_required
@token.manager_required
def review_note_update(note_id):
    current_user = get_current_user()
    if request.method == "DELETE":    
        docs = mongo.db.weekly_notes.remove({
            "_id": ObjectId(note_id),
            "manager_id": str(current_user['_id']),
        })
        return jsonify({"status":"success"}), 200    
    if request.method == "PUT":
        comment = request.json.get("comment",None)
        junior_id = request.json.get("junior_id",None)
        rep = mongo.db.weekly_notes.update({
                "_id":ObjectId(note_id),
                    }, {
                    "$set": {
                        "comment":comment,
                        "manager_id":str(current_user['_id']),
                        "junior_id":junior_id,
                        "updated_at":datetime.datetime.utcnow(),
                        "type":"weekly_note"
                         }
                    },upsert=True)
        return jsonify({"status":"success"}), 200



def dashboard_details(data):
    user_data = data['user']
    user_data = (load_user(user_data))
    data['user'] = user_data
    if 'review' in data:
        review_detail = data['review']
        for elem in review_detail:
            elem['manager_id'] = load_manager(ObjectId(elem['manager_id']))    
    else:
        review_detail = None
    return data


@bp.route('/dashboard_profile/<string:id>', methods=['GET'])
@jwt_required
@token.admin_required
def dashboard_profile(id):
    ret = mongo.db.users.find_one({
        "_id": ObjectId(id)
    })
    ret["_id"] = str(ret["_id"])
    if "kpi_id" in ret and ret["kpi_id"] is not None:
        ret_kpi = mongo.db.kpi.find_one({
            "_id": ObjectId(ret["kpi_id"])
        })
        ret_kpi["_id"] = str(ret_kpi['_id'])
        ret['kpi'] = ret_kpi
    else:
        ret['kpi'] = {}
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
        }).sort("created_at", 1)
        docs = [load_details(serialize_doc(doc)) for doc in docs]
        report = mongo.db.reports.find({
                "user": str(id),
                "type": "monthly",
                "created_at": {
                    "$gte":reset_time
                    }                
            })
        report = [dashboard_details(serialize_doc(doc)) for doc in report]
        ret['is_reset'] = True
    else:
        docs = mongo.db.reports.find({
            "user": str(id),
            "type": "weekly"
        }).sort("created_at", 1)
        docs = [load_details(serialize_doc(doc)) for doc in docs]
        report = mongo.db.reports.find({
                "user": str(id),
                "type": "monthly"
            })
        report = [dashboard_details(serialize_doc(doc)) for doc in report]
        ret['is_reset'] = False
    return jsonify({"profile":ret,"weekly":docs, "monthly":report})



@bp.route('/old_ratings/<string:id>', methods=['GET'])
@jwt_required
@token.admin_required
def old_ratings(id):
    state = mongo.db.users.find_one({
        "_id": ObjectId(id),
        "rating_reset_time": {"$exists": True}
    }, {"rating_reset_time": 1, '_id': 0})
    if state is not None:
        ret = mongo.db.users.find_one({
        "_id": ObjectId(id)
        })
        ret["_id"] = str(ret["_id"])
        if "kpi_id" in ret and ret["kpi_id"] is not None:
            ret_kpi = mongo.db.kpi.find_one({
                "_id": ObjectId(ret["kpi_id"])
            })
            ret_kpi["_id"] = str(ret_kpi['_id'])
            ret['kpi'] = ret_kpi
        else:
            ret['kpi'] = {}
        reset_time = state['rating_reset_time']
        docs = mongo.db.reports.find({
            "user": str(id),
            "type": "weekly",
            "created_at": {
                "$lt":reset_time
                }
        }).sort("created_at", 1)
        docs = [load_details(serialize_doc(doc)) for doc in docs]
        report = mongo.db.reports.find({
                "user": str(id),
                "type": "monthly",
                "created_at": {
                    "$lt":reset_time
                    }
            })
        report = [dashboard_details(serialize_doc(doc)) for doc in report]
        return jsonify({"profile":ret,"weekly":docs, "monthly":report})




@bp.route('/test_messages/<string:message_type>/<string:message_key>', methods=['GET'])
def test_message(message_type,message_key): 
    user = {
        "Checkin_rating":95.23809523809524,
        "Monthly_rating":{"451ffec763be4b77998b4c51c16c7d6e":5.0,"461e82f521f54c19b5ffa31fb2c5ce0a":7.5,"5b57cd224ef945d5975d03e3e0c6f4b8":6.0,"88b36372ad534d5d8f200a8c6c6fd348":8.0,"9a0eda932b9f4eb2a25dd9935c7d2f91":3.5,"d253ef072c034a228d223cd99d4a616f":6.5,"eb547671f6d548fd9af77a3da0fc893e":7.0},
        "Overall_rating":6.3076923076923075,
        "_id":"5cdf9148daea4ba0e2ca80a0",
        "cron_checkin":True,
        "dateofjoining":"Thu, 07 Mar 2019 00:00:00 GMT",
        "dob":"1997-09-11",
        "gender":"Male",
        "id":"462",
        "job_title":"Jr. Python Developer",
        "jobtitle":"Jr. Python Developer",
        "kpi":{"_id":"5cdfa672917623516fdb7fea",
        "era_json":[{"ID":"7942dbbc7996420b80daddb329f1f57f","addEra":False,"desc":"","edit":False,"title":""},
        {"ID":"9a0eda932b9f4eb2a25dd9935c7d2f91","desc":"Able to start client project under supervision or on his own","edit":False,"title":"Client Project"},
        {"ID":"88b36372ad534d5d8f200a8c6c6fd348","desc":"Able to start working on in house projects, but mainly able to suggest ideas, solve issues, communicate effectively show good resourcefulness in house projects. ","edit":False,"title":"Inhouse Project"},
        {"ID":"451ffec763be4b77998b4c51c16c7d6e","desc":"Able to suggest ideas for team improvement in terms new tech improvements, paying attention to common issues basically overall contribute to team growth/effectiveness. ","edit":False,"title":"Team Contribution"},
        {"ID":"76131e38ca6b41b5a2ab3a6b60395e5a","desc":"","edit":False,"title":""}],
        "kpi_json":[{"ID":"970260b1b6a948a4b53be02e1e953772","addKpi":False,"desc":"","edit":False,"title":""},
        {"ID":"5b57cd224ef945d5975d03e3e0c6f4b8","desc":"Able to learn/implement new things in the same technology stack. New modules/libraries which are not part of training module, its expected trainee is able to learn and implement those with minimum supervision","edit":False,"title":"Learning Curve"},
        {"ID":"eb547671f6d548fd9af77a3da0fc893e","desc":"Able to quickly grasp and learn the technology assigned. Should be able to demonstrate good understanding and learning to senior/ mentor assigned.\nAble to solve basic problems and debug issues themselves. ","edit":False,"title":"Technology"},
        {"ID":"461e82f521f54c19b5ffa31fb2c5ce0a","desc":"Able to communicate well over slack, with team members and seniors. Write proper standups, reports and overall able to communicate well over slack/email","edit":False,"title":"Communication"},
        {"ID":"d253ef072c034a228d223cd99d4a616f","desc":"Understand hr system, company polices follow them properly. ","edit":False,"title":"Follow Company Policy HR System"}],"kpi_name":"Trainee"},
        "kpi_id":"5cdfa672917623516fdb7fea","last_login":"Thu, 29 Aug 2019 13:49:42 GMT",
        "managers":[{"_id":"5cdf9147daea4ba0e2ca807c","job_title":"CEO","profileImage":"https://secure.gravatar.com/avatar/770e9e63ec55f1a9c5915f1e37d8e66d.jpg?s=192&d=https%3A%2F%2Fa.slack-edge.com%2F00b63%2Fimg%2Favatars%2Fava_0023-192.png","username":"manish","weight":10}],
        "missed_chechkin_crone":False,"missed_checkin_dates":[{"created_at":"Fri, 28 Jun 2019 11:30:07 GMT","date":"2019-06-27"},
        {"created_at":"Wed, 03 Jul 2019 11:30:15 GMT","date":"2019-07-02"}],
        "name":"Aishwary Kaul","profile":None,"profileImage":"https://avatars.slack-edge.com/2019-05-04/628636263670_d8c7412e29ad9d1ff23b_192.jpg","project_difficulty":0.7142857142857143,"role":"Employee",
        "slack_id":"UGRRJKCMB",
        "status":"Enabled",
        "team":"Python",
        "user_Id":"481",
        "username":"aishwary",
        "work_email":"aishwary@excellencetechnologies.in",
        "email":"aishwary@excellencetechnologies.in"}
    
    user_detail = json.loads(json.dumps(user,default=json_util.default))
    payload = {
        "message_key": message_key,
        "message_type": message_type,
        "data" : "data",
        "user": user_detail
        }    
    notification_message_test = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname,json=payload)
    return  (notification_message_test.text)