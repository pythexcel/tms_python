from app import mongo
from app import token
from app.util import serialize_doc
import datetime
from flask import (
    Blueprint, flash, jsonify, abort, request
)

from bson.objectid import ObjectId


from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity, get_current_user, jwt_refresh_token_required,
    verify_jwt_in_request
)

bp = Blueprint('user', __name__, url_prefix='/user')


@bp.route('/list', methods=['GET'])
@jwt_required
@token.admin_required
def user_list():
    users = mongo.db.users.find({},{"profile":0})
    users = [serialize_doc(user) for user in users]
    return jsonify(users), 200



@bp.route('/role/<string:user_id>/<string:role>', methods=['PUT'])
@jwt_required
@token.admin_required
def user_assign_role(user_id, role):
    if role == "admin" or role == "manager":
        ret = mongo.db.users.update({
            "_id": ObjectId(user_id)
        }, {
            "$set": {
                "role": role
            }
        }, upsert=False)
        return jsonify(ret), 200
    else:
        return jsonify(msg="invalid role"), 500

    
    
   
@bp.route("/recent_activity", methods=["GET"])
@jwt_required
def recent_activity():
        # First take date time where weekly report is to be dealt with
        today = datetime.date.today()
        last_sunday = today - datetime.timedelta(days=(today.weekday() + 1))
        last_monday = today - datetime.timedelta(days=(today.weekday() + 8))
        
        # Get current user 
        current_user = get_current_user()
        # Check if current user is Admin or manager
        if current_user["role"] == "Admin" or "manager":
            # First find the users which have the manager id in it's document
            users = mongo.db.users.find({
                "managers": {
                    "$elemMatch": {"_id": str(current_user["_id"])}
                }
                })
            # Make a list of User_id and then fetch all the users/juniors belong to that manager
            user_ids = []
            for user in users:
                user_ids.append(str(user['_id']))
            # Now find weekly reports of all those users_id in the above list whose report is not reviewd   
            for data in  user_ids:
                docs = mongo.db.reports.find({
                    "user":str(data),
                    "review": {'$exists': False},
                    "type" : "weekly",
                    "created_at": {
                    "$gte": datetime.datetime(last_monday.year, last_monday.month, last_monday.day),
                    "$lte": datetime.datetime(last_sunday.year, last_sunday.month, last_sunday.day)
                     }  
                })
                docs = [serialize_doc(doc) for doc in docs]
                # Append those user records whose not been reviewd in user_id list
                user_id = []
                for user in docs:
                    user_id.append(user)
                # Then if we find that data exist in user_id report than update the manager recent activity with a date and message    
                if user_id is not None: 
                    ret = mongo.db.recent_activity.update({
                    "user": str(current_user["_id"]),},
                    {"$set":{"recent_activity":{
                    "created_at": datetime.datetime.now(),
                    "Message":"Your have not reviewed your juniors weekly report"
                    }}},upsert=True)
                return jsonify(str(ret))       
        # Here we see the recent activity of normal employee or whose role is not manager or admin    
        else:
            # First let's find the weekly reports who have been reviewd by manager 
            docs = mongo.db.reports.find({
                "user": str(current_user["_id"]),
                "review": {'$exists': True},
                "type" : "weekly",
                "created_at": {
                "$gte": datetime.datetime(last_monday.year, last_monday.month, last_monday.day),
                "$lte": datetime.datetime(last_sunday.year, last_sunday.month, last_sunday.day)
            }
            })
            # Here see if we find a reviewed report in  a particular time from the above condition 
            docs = [serialize_doc(doc) for doc in docs]
            if not docs:
                return("review not available")
            # if report is find reviewd which are generated within a week set a recent activity for normal employee with datetime and message
            else:
                ret = mongo.db.recent_activity.update({
                    "user": str(current_user["_id"]),},
                    {"$set":{"recent_activity":{
                    "created_at": datetime.datetime.now(),
                    "user": str(current_user["_id"] ),
                    "Message":"Your weekly report has been reviewed"
                    }}},upsert=True)
                
            last_day = today - datetime.timedelta(1)
            next_day = today + datetime.timedelta(1)
            # Here we see if user has done its daily checkin or not
            # Find daily checkin type in reports within a particular time if report is find it's fine 
            reports = mongo.db.reports.find({
            "user": str(current_user["_id"]),
            "type": "daily",
            "created_at": {
                "$gte": datetime.datetime(last_day.year, last_day.month, last_day.day),
                "$lte": datetime.datetime(next_day.year, next_day.month, next_day.day)
            }
            })
            reports = [serialize_doc(report) for report in reports]
            # if report is not fined add a message in user recent activity with a message
            if not reports:
                ret = mongo.db.recent_activity.update({
                    "user": str(current_user["_id"]),},
                    {"$set":{"recent_activity":{
                        "checkin_message":"You have missed your daily checkin"
                    }}},upsert=True)
            return jsonify(docs), 200
