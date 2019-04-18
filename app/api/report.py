from app import token
from app import mongo
from app.util import serialize_doc, get_manager_profile
from flask import (
    Blueprint, flash, jsonify, abort, request
)

from bson.objectid import ObjectId

import datetime


from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity, get_current_user, jwt_refresh_token_required,
    verify_jwt_in_request
)

bp = Blueprint('report', __name__, url_prefix='/')


@bp.route('/checkin', methods=["POST"])
@jwt_required
def add_checkin():
    if not request.json:
        abort(500)

    report = request.json.get("report", None)
    task_completed = request.json.get("task_completed", False)
    task_not_completed_reason = request.json.get(
        "task_not_completed_reason", "")
    highlight = request.json.get("highlight", "")

    if task_completed == 1:
        task_completed = True
    else:
        task_completed = False

    current_user = get_current_user()

    ret = mongo.db.reports.insert_one({
        "report": report,
        "task_completed": task_completed,
        "task_not_completed_reason": task_not_completed_reason,
        "highlight": highlight,
        "user": str(current_user["_id"]),
        "created_at": datetime.datetime.now(),
        "type": "daily"
    }).inserted_id
    return jsonify(str(ret)), 200


@bp.route('/reports', methods=["GET"])
@jwt_required
def checkin_reports():
    current_user = get_current_user()
    docs = mongo.db.reports.find({
        "user": str(current_user["_id"])
    })
    docs = [serialize_doc(doc) for doc in docs]
    return jsonify(docs), 200


@bp.route('/week_reports', methods=["GET"])
@jwt_required
def get_week_reports():
    current_user = get_current_user()

    today = datetime.date.today()
    last_sunday = today - datetime.timedelta(days=(today.weekday() + 1))
    last_monday = today - datetime.timedelta(days=(today.weekday() + 8))

    docs = mongo.db.reports.find({
        "user": str(current_user["_id"]),
        "created_at": {
            "$gte": last_monday.isoformat(),
            "$lte": last_sunday.isoformat()
        }
    })
    docs = [serialize_doc(doc) for doc in docs]

    return jsonify(docs), 200


@bp.route('/weekly', methods=["POST", "GET"])
@jwt_required
def add_weekly_checkin():
    current_user = get_current_user()
    if request.method == "GET":
        docs = mongo.db.reports.find({
            "type": "weekly",
            "user": str(current_user["_id"])
        }).sort("created_at", 1)
        docs = [serialize_doc(doc) for doc in docs]
        return jsonify(docs), 200
    if not request.json:
        abort(500)

    k_highlight = request.json.get("k_highlight", None)
    extra = request.json.get("extra", "")
    select_days = request.json.get("select_days", [])
    difficulty = request.json.get("difficulty", 0)

    if k_highlight is None:
        return jsonify({"msg": "Invalid request"}), 500

    ret = mongo.db.reports.insert_one({
        "k_highlight": k_highlight,
        "extra": extra,
        "select_days": select_days,
        "user": str(current_user["_id"]),
        "created_at": datetime.datetime.now(),
        "type": "weekly",
        "is_reviewed": False,
        "difficulty": difficulty
    }).inserted_id
    return jsonify(str(ret)), 200


def get_manager_juniors(id):

    users = mongo.db.users.find({
        "managers": {
            "$elemMatch": {"_id": str(id)}
        }
    })
    user_ids = []
    for user in users:
        user_ids.append(str(user['_id']))
    return user_ids


def load_checkin(id):
    ret = mongo.db.report.find_one({
        "_id": ObjectId(id)
    })
    return serialize_doc(ret)


def add_checkin_data(weekly_report):
    select_days = weekly_report["select_days"]
    select_days = [load_checkin(day) for day in select_days]
    weekly_report["select_days"] = select_days
    return weekly_report


@bp.route("/manager_weekly_all", methods=["GET"])
@jwt_required
@token.manager_required
def get_manager_weekly_list_all():
    current_user = get_current_user()
    juniors = get_manager_juniors(current_user['_id'])
    docs = mongo.db.reports.find({
        "type": "weekly",
        "user": {
            "$in": juniors
        }
    }).sort("created_at", 1)
    docs = [add_checkin_data(serialize_doc(doc)) for doc in docs]
    return jsonify(docs), 200


@bp.route("/manager_weekly", methods=["GET"])
@bp.route("/manager_weekly/<string:weekly_id>", methods=["POST"])
@jwt_required
@token.manager_required
def get_manager_weekly_list(weekly_id=None):

    current_user = get_current_user()
    if request.method == "GET":
        juniors = get_manager_juniors(current_user['_id'])

        docs = mongo.db.reports.find({
            "type": "weekly",
            "is_reviewed": False,
            "user": {
                "$in": juniors
            }
        }).sort("created_at", 1)
        docs = [add_checkin_data(serialize_doc(doc)) for doc in docs]
        return jsonify(docs), 200
    else:
        if not request.json:
            abort(500)

        difficulty = request.json.get("difficulty", 0)
        rating = request.json.get("rating", 0)
        comment = request.json.get("comment", None)

        if comment is None or weekly_id is None:
            return jsonify(msg="invalid request"), 500

        ret = mongo.db.reports.update({
            "_id": ObjectId(weekly_id)
        }, {
            "$set": {
                "review": {
                    "difficulty": difficulty,
                    "rating": rating,
                    "comment": comment
                },
                "is_reviewed": True
            }
        }, upsert=False)

        return jsonify(ret)
    
    

@bp.route("/overall_reviewes/<string:user_id>", methods=["GET"])
@jwt_required
def overall_reviewes(user_id):
    docs = mongo.db.reports.find({"user":user_id})
    user = mongo.db.users.find_one({"_id":ObjectId(user_id)})
    weights = user['managers']
    manager_weight = weights[0]
    weight = manager_weight['weight']  
    docs = [serialize_doc(doc) for doc in docs]
    sum=0
    for detail in docs:   
       review=detail['review']
       rating=review['rating']
       sum=sum+(rating*weight)
    overall_rating = sum /weight
    return jsonify(overall_rating)
    
    
    
  
@bp.route("/360_reviewers", methods=["GET"])
@jwt_required
def review_360():
    current_user = get_current_user()
    user = mongo.db.users.find_one({
        "_id": ObjectId(current_user["_id"])
    })
    if "managers" not in user:
        return []
    else:
        ret = [get_manager_profile(manager) for manager in user["managers"]]
        return jsonify(ret)


@bp.route("/360_reviews", methods=["GET", "POST"])
@bp.route("/360_reviews/<string:review_id>", methods=["PUT"])
@jwt_required
def reviews_360(review_id=None):
    current_user = get_current_user()

    if request.method == "GET":
        docs = mongo.db.reviews_360.find({
            "user": current_user["_id"]
        })
        docs = [serialize_doc(doc) for doc in docs]
        print(docs)
        return jsonify(docs)

    if not request.json:
        abort(500)

    manager = request.json.get("manager", None)
    rating = request.json.get("rating", None)
    comment = request.json.get("comment", "")
    anon = request.json.get("anon", True)

    if manager is None or rating is None:
        abort(500)

    if anon == 0:
        anon = False
    else:
        anon = True

    if rating is None:
        abort(500)

    if not anon:
        user = current_user["_id"]
    else:
        user = ""
    if review_id is None:
        ret = mongo.db.reviews_360.insert_one({
            "rating": rating,
            "comment": comment,
            "anon": anon,
            "user": user
        }).inserted_id
        ret = str(ret)
    else:
        ret = mongo.db.reviews_360.update({
            "_id": ObjectId(review_id)
        }, {
            "$set": {
                "rating": rating,
                "comment": comment,
                "anon": anon,
                "user": user
            }
        })

    return jsonify(ret)
