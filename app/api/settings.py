from flask import (
   Blueprint, g, request, abort, jsonify)
from app import mongo
from flask_jwt_extended import (
    jwt_required, create_access_token, get_current_user
)
from app import token
from bson import ObjectId
from app.util import serialize_doc


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
        ret = mongo.db.slack_tokens.update({
        }, {
            "$set": {
                "webhook_url": webhook_url,
                "slack_token": slack_token
            }
        },upsert=True)
        return jsonify(str(ret))

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
        ret = mongo.db.schdulers_setting.update({
            },{
                "$set":{
                "monthly_remainder": monthly_remainder,
                "weekly_remainder": weekly_remainder,
                "recent_activity": recent_activity,
                "review_activity": review_activity,
                "monthly_manager_reminder": monthly_manager_reminder
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
        return jsonify(ret)
    if request.method == "PUT":
        monthly_remainder = request.json.get("monthly_remainder")
        weekly_remainder1 = request.json.get("weekly_remainder1")
        weekly_remainder2 = request.json.get("weekly_remainder2")
        review_activity = request.json.get("review_activity")
        monthly_manager_reminder = request.json.get("monthly_manager_reminder")
        missed_checkin = request.json.get("missed_checkin")
        ret = mongo.db.schdulers_msg.update({
        }, {
            "$set": {
                "monthly_remainder": monthly_remainder,
                "weekly_remainder1": weekly_remainder1,
                "weekly_remainder2":weekly_remainder2,
                "review_activity":review_activity,
                "monthly_manager_reminder":monthly_manager_reminder,
                "missed_checkin":missed_checkin
            }
        })
        return jsonify(str(ret))
