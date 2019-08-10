from flask import (
   Blueprint, g, request, abort, jsonify)
from app import mongo
from flask_jwt_extended import (
    jwt_required, create_access_token, get_current_user
)
from app import token
from bson import ObjectId
from app.util import serialize_doc
from app.config import default
import datetime
from dateutil.relativedelta import relativedelta


bp = Blueprint('system', __name__, url_prefix='/system')


@bp.route('/settings', methods=['POST'])
@jwt_required
def settings():
 user = get_current_user()
 if user["role"] == "Admin":   
    if not request.json:
        abort(500)
    integrate_with_hr = request.json.get('integrate_with_hr', False)
    if integrate_with_hr is True:
        hr = mongo.db.hr.insert_one({
            "integrate_with_hr": integrate_with_hr
        }).inserted_id
        return jsonify(str(hr))
    else:
        hr = mongo.db.hr.update({
            "integrate_with_hr": True
        }, {
                "$unset": {
                     "integrate_with_hr": integrate_with_hr
                 }
             })
        return ("settings off")

   
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
        webhook_url = request.json.get("webhook_url")
        slack_token = request.json.get("slack_token")
        secret_key =request.json.get("secret_key")
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
        revew_360_setting=request.json.get("revew_360_setting",True)
        missed_reviewed=request.json.get("missed_reviewed",True)
        skip_review_setting=request.json.get("managerSkip",True)
        weekly_automated=request.json.get("weekly_automated",True)
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
                "weekly_automated":weekly_automated
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


