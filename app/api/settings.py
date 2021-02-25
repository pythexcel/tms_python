from flask import (
   Blueprint, g, request, abort, jsonify)
from app import mongo
from flask_jwt_extended import (
    jwt_required, create_access_token, get_current_user
)
from app import token
from app.config import notification_system_url,accountname
from bson import ObjectId
from app.util import serialize_doc
import datetime
from dateutil.relativedelta import relativedelta
from bson import json_util
import json
import requests

bp = Blueprint('system', __name__, url_prefix='/system')


#Api for weekly and monthly settings.
@bp.route('put/reports_settings', methods=["PUT"])
@jwt_required
@token.admin_required
def reports_settings():

    if request.method == "PUT":
        weekly_status = request.json.get("weekly_status",True)
        monthly_status = request.json.get("monthly_status",True)

        ret = mongo.db.schdulers_setting.update({
            },{
                "$set":{
                    "monthly_remainder": weekly_status,
                    "monthly_manager_reminder": weekly_status,
                    "weekly_remainder": monthly_status,
                    "review_activity": monthly_status,
                    "weekly_status": weekly_status,
                    "monthly_status": monthly_status
            }}, upsert=True)
        return jsonify({"status":"success"})

def reset_dict(user_id):
    docs = mongo.db.reports.find({"user": str(user_id), "type": "monthly"})
    docs = [serialize_doc(doc) for doc in docs]
    if docs:
        all_ids = []
        for detail in docs:
            if 'review' in detail:
                for review in detail['review']:
                    for data in review['comment']['kpi']:
                        if data['id'] not in all_ids:
                            all_ids.append(data['id'])
                    for data in review['comment']['era']:
                        if data['id'] not in all_ids:
                            all_ids.append(data['id'])
            else:
                return None
        user_details = mongo.db.users.find_one({"_id":ObjectId(user_id)},{"Monthly_rating":1,"_id":0})
        if user_details is not None:
            monthly_kpis = user_details['Monthly_rating']
            if all_ids:
                for all_id in all_ids:
                    if all_id in monthly_kpis:
                        reset_dict = {""+all_id+"":0}
                        monthly_kpis.update(reset_dict)
                return monthly_kpis
            else:
                return None
        else:
            return None    
    else:
        return None
#Api for reset person overall rating    
@bp.route('/rating_reset/<string:user_id>', methods=["PUT"])
@jwt_required
@token.admin_required
def rating_reset(user_id):
    if request.method == "PUT":
        reason = request.json.get("msg",None)
        ret = mongo.db.users.update({
            "_id": ObjectId(user_id)
        }, {
            "$set": {
                "Overall_rating": 0,
                "rating_reset_time":datetime.datetime.utcnow()
            }
        },upsert=True)
        monthly_kpis = reset_dict(user_id)
        print(monthly_kpis)
        if monthly_kpis is not None:
            docs = mongo.db.users.update({
                    "_id": ObjectId(user_id)
                }, {
                    "$set": {
                        "Monthly_rating":monthly_kpis
                    }})
        else:
            pass
        users = mongo.db.users.find_one({
            "_id": ObjectId(user_id)
        })
        user_info = serialize_doc(users)
        print(user_info)
        if reason is not None:
            user = json.loads(json.dumps(user_info,default=json_util.default))
            rating_reset = {"user":user,
                        "data":{"message":reason},"message_key":"rating_reset_with_comment","message_type":"simple_message"}
            notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname,json=rating_reset)

        else:
            user = json.loads(json.dumps(user_info,default=json_util.default))
            rating_reset = {"user":user,
                        "data":None,"message_key":"rating_reset","message_type":"simple_message"}
            notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname,json=rating_reset)
        return jsonify({"status":"success"})


#reset rating for all employees together

@bp.route('/ResetAllRatings', methods=["PUT"])
@jwt_required
@token.admin_required
def ResetAllRatings():
    if request.method == "PUT":
        #Finding all users addresses rest admin
        users = mongo.db.users.find({
            "role":{"$ne":"Admin"}
        }).distinct("_id")
        #Update all users overall rating and puting reset rating time
        ret = mongo.db.users.update({
            "_id": {
                "$in": users
            }}, {
            "$set": {
                "Overall_rating": 0,
                "rating_reset_time":datetime.datetime.utcnow()
            }
        },multi=True)
        for user_id in users:
            #calling function for reset monthly rating for each employee with same kpi id and update kpi with 0 ratings
            monthly_kpis = reset_dict(str(user_id))
            if monthly_kpis is not None:
                docs = mongo.db.users.update({
                        "_id": ObjectId(str(user_id))
                    }, {
                        "$set": {
                            "Monthly_rating":monthly_kpis
                        }})
            else:
                pass
            #fetching user profile for sending notification
            users = mongo.db.users.find_one({
                "_id": ObjectId(str(user_id))
            })
            user_info = serialize_doc(users)
            #sending notification 
            user = json.loads(json.dumps(user_info,default=json_util.default))
            rating_reset = {"user":user,
                        "data":None,"message_key":"rating_reset","message_type":"simple_message"}
            notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname,json=rating_reset)
        return jsonify({"status":"success"})

   
#Api for slack token settings   
@bp.route('/slack_settings', methods=["PUT","GET"])
@jwt_required
@token.admin_required
def slack_setings():
    if request.method == "GET":
        users = mongo.db.slack_tokens.find({})
        users = [serialize_doc(doc) for doc in users]
        return jsonify(users)

    if request.method == "PUT":
        slack_token = request.json.get("slack_token")
        ret = mongo.db.slack_tokens.update({
        }, {
            "$set": {
                "webhook_url": webhook_url,
                "slack_token": slack_token,
                "secret_key":secret_key
            }
        },upsert=True)
        return jsonify(str(ret))


@bp.route('/remove_previous_checkin', methods=['DELETE'])
@jwt_required
@token.admin_required
def remove_months_checkin():
    six_months = datetime.datetime.today() + relativedelta(months=-6)
    print(six_months)
    # find report greater than last 6 month date
    ret = mongo.db.reports.find({"type":"daily","created_at":{"$lte":six_months}
    })
    docs = [serialize_doc(doc) for doc in ret]
    # find the reports and store in diffrent collection
    for data_id in docs:
        if "cron_checkin" in data_id:
            cron_checkin = data_id['cron_checkin']
        else:
            cron_checkin = ""
        ser = mongo.db.archive_report.find_one({"_id":data_id['_id']})
        if not ser:
            ret = mongo.db.archive_report.insert({
                "_id":data_id['_id'],
                "created_at": data_id['created_at'],
                "cron_checkin": cron_checkin,
                "highlight":data_id['highlight'],
                "highlight_task_reason":data_id['highlight_task_reason'],
                "report":data_id['report'],
                "task_completed":data_id['task_completed'],
                "task_not_completed_reason":data_id['task_not_completed_reason'],
                "type":data_id['type'],
                "user":data_id['user'],
                "username":data_id['username'],
                })
        else:
            pass        
    # delete the reports from report collection    
    user_id = []
    for elem in docs:
        user_id.append(ObjectId(elem["_id"]))
    nap = mongo.db.reports.remove({
        "_id": {"$in":user_id}
    })    
    return jsonify(str({"msg":"Check-in archived","Date": datetime.datetime.utcnow()})), 200


@bp.route('/remove_disable_user', methods=['DELETE'])
@jwt_required
@token.admin_required
def remove_disable_user():
    ret = mongo.db.users.find({"status": "Disable"})
    docs = [serialize_doc(doc) for doc in ret]
    # find the reports and store in diffrent collection
    for data_id in docs:
        if "cron_checkin" in data_id:
            cron_checkin = data_id['cron_checkin']
        else:
            cron_checkin = ""
        if "missed_chechkin_crone" in data_id:
            missed_chechkin_crone = data_id['missed_chechkin_crone']
        else:
            missed_chechkin_crone = ""
        ser = mongo.db.disable_users.find_one({"_id": data_id['_id']})
        if not ser:
            ret = mongo.db.disable_users.insert({
                "_id":
                data_id['_id'],
                "username":
                data_id['username'],
                "id":
                data_id['id'],
                "name":
                data_id['name'],
                "user_Id":
                data_id['user_Id'],
                "status":
                data_id['status'],
                "jobtitle":
                data_id['jobtitle'],
                "dob":
                data_id['dob'],
                "gender":
                data_id['gender'],
                "work_email":
                data_id['work_email'],
                "slack_id":
                data_id['slack_id'],
                "profileImage":
                data_id['profileImage'],
                "dateofjoining":
                data_id['dateofjoining'],
                "last_login":
                data_id['last_login'],
                "team":
                data_id['team'],
                "role":
                data_id['role'],
                "cron_checkin":
                cron_checkin,
                "missed_chechkin_crone":
                missed_chechkin_crone
            })
        else:
            pass
    # delete the reports from report collection
    user_id = []
    for elem in docs:
        user_id.append(ObjectId(elem["_id"]))
    nap = mongo.db.users.remove({"_id": {"$in": user_id}})
    return jsonify({
        "msg": "Users Removed from User Collection",
        "Date": datetime.datetime.utcnow()
    }), 200    


#Api for schdulers on off settings
@bp.route('/schdulers_settings', methods=["GET","PUT"])
@jwt_required
@token.admin_required
def schdulers_setings():
    if request.method == "GET":
        ret = mongo.db.schdulers_setting.find({
        })
        ret = [serialize_doc(doc) for doc in ret]
        return jsonify(ret)

    if request.method == "PUT":
        monthly_remainder = request.json.get("monthly_remainder")
        weekly_remainder = request.json.get("weekly_remainder")
        recent_activity = request.json.get("recent_activity")
        review_activity = request.json.get("review_activity")
        monthly_manager_reminder = request.json.get("monthly_manager_reminder")
        revew_360_setting=request.json.get("revew_360_setting")
        missed_reviewed=request.json.get("missed_reviewed")
        skip_review_setting=request.json.get("managerSkip")
        only_manager_skip_setting=request.json.get("only_manager_skip")
        weekly_automated=request.json.get("weekly_automated")
        easyRating=request.json.get("easyRating")
        ret = mongo.db.schdulers_setting.update({
            },{
                "$set":{
                "monthly_remainder": monthly_remainder,
                "weekly_remainder": weekly_remainder,
                "recent_activity": recent_activity,
                "review_activity": review_activity,
                "monthly_manager_reminder": monthly_manager_reminder,
                "revew_360_setting":revew_360_setting,
                "missed_reviewed":missed_reviewed,
                "skip_review":skip_review_setting,
                "only_manager_skip":only_manager_skip_setting,
                "weekly_automated":weekly_automated,
                "easyRating":easyRating
            }}, upsert=True)
        return jsonify(str(ret))


#Api for schdulers mesg settings
@bp.route('/schduler_mesg', methods=["GET","PUT"])
@jwt_required
@token.admin_required
def slack_schduler():
    if request.method == "GET":
        ret = mongo.db.schdulers_msg.find({
        })
        ret = [serialize_doc(doc) for doc in ret]
        return jsonify([default] if not ret else ret)
    if request.method == "PUT":
        monthly_remainder = request.json.get("monthly_remainder")
        weekly_remainder1 = request.json.get("weekly_remainder1")
        weekly_remainder2 = request.json.get("weekly_remainder2")
        review_activity = request.json.get("review_activity")
        monthly_manager_reminder = request.json.get("monthly_manager_reminder")
        missed_checkin = request.json.get("missed_checkin")
        weekly_report_mesg=request.json.get("weekly_report_mesg")
        monthly_report_mesg=request.json.get("monthly_report_mesg")
        missed_review_msg = request.json.get("missed_reviewed_mesg")
        ret = mongo.db.schdulers_msg.update({
        }, {
            "$set": {
                "monthly_remainder": monthly_remainder,
                "weekly_remainder1": weekly_remainder1,
                "weekly_remainder2":weekly_remainder2,
                "review_activity":review_activity,
                "monthly_manager_reminder":monthly_manager_reminder,
                "missed_checkin":missed_checkin,
                "weekly_report_mesg":weekly_report_mesg,
                "monthly_report_mesg":monthly_report_mesg,
                "missed_reviewed_mesg":missed_review_msg
            }
        },upsert=True)
        return jsonify(str(ret))


