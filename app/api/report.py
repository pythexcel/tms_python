from app import token
from app import mongo
from app.util import serialize_doc, get_manager_profile
from flask import (
    Blueprint, flash, jsonify, abort, request
)

from bson.objectid import ObjectId
from app.util import slack_message
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
    date = request.json.get("date", "")
    highlight_task_reason = request.json.get("highlight_task_reason", None)
    today = datetime.datetime.today()
    next_day = today + datetime.timedelta(days=1)

    if not report:
          return jsonify({"msg": "Invalid Request"}), 400

    if task_completed == 1:
        task_completed = True
    else:
        task_completed = False

    current_user = get_current_user()
    username = current_user['username']

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
                    "type": "daily"
                }})
        else:
            ret = mongo.db.reports.insert_one({
                "report": report,
                "task_completed": task_completed,
                "task_not_completed_reason": task_not_completed_reason,
                "highlight": highlight,
                "highlight_task_reason": highlight_task_reason,
                "user": str(current_user["_id"]),
                "created_at": date_time,
                "type": "daily"
            }).inserted_id

        docs = mongo.db.recent_activity.update({
            "user": str(current_user["_id"])},
            {"$push": {"Daily_checkin": {
                "created_at": date_time,
                "priority": 0,
                "Daily_chechkin_message": date_time
            }}}, upsert=True)
        slack_message(msg=username+ " "+'have created daily chechk-in at'+' '+str(formatted_date))
        return jsonify(str(ret))
    else:
        date_time = datetime.datetime.strptime(date, "%Y-%m-%d")
        rep = mongo.db.reports.find_one({
            "user": str(current_user["_id"]),
            "type": "daily",
            "created_at": {
                "$gte": datetime.datetime(today.year, today.month, today.day),
                "$lte": datetime.datetime(next_day.year, next_day.month, next_day.day)
            }
        })
        if rep is not None:
            ret = mongo.db.reports.update({
                "user": str(current_user["_id"]),
                "created_at": date_time
            }, {
                "$set": {
                    "report": report,
                    "task_completed": task_completed,
                    "task_not_completed_reason": task_not_completed_reason,
                    "highlight": highlight,
                    "highlight_task_reason": highlight_task_reason,
                    "user": str(current_user["_id"]),
                    "created_at": date_time,
                    "type": "daily"
                }},upsert=True)
        else:
            ret = mongo.db.reports.insert_one({
                "report": report,
                "task_completed": task_completed,
                "task_not_completed_reason": task_not_completed_reason,
                "highlight": highlight,
                "highlight_task_reason": highlight_task_reason,
                "user": str(current_user["_id"]),
                "created_at": date_time,
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
        return jsonify(str(ret))

@bp.route('/reports', methods=["GET"])
@jwt_required
def checkin_reports():
    current_user = get_current_user()
    docs = mongo.db.reports.find({
        "user": str(current_user["_id"])
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
    username = current_user['username']
    profileimage = current_user['profileImage']
    job_title = current_user['jobtitle']
    team = current_user['team']

    if not k_highlight:
        return jsonify({"msg": "Invalid Request"}), 400
    
    reviewed = False
    users = mongo.db.users.find({
        "_id": ObjectId(current_user["_id"])
    })
    users = [serialize_doc(doc) for doc in users]

    managers_data = []
    for data in users:
        for mData in data['managers']:
            mData['reviewed'] = reviewed
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
    
    ret = mongo.db.reports.insert_one({
        "k_highlight": k_highlight,
        "extra": extra,
        "select_days": select_days,
        "user": str(current_user["_id"]),
        "username": username,
        "created_at": datetime.datetime.now(),
        "type": "weekly",
        "is_reviewed": managers_data,
        "profileImage": profileimage,
        "jobtitle": job_title,
        "team": team,
        "cron_checkin": True,
        "cron_review_activity": False,
        "kpi_json": kpi_name,
        "era_json": era_name,
        "difficulty": difficulty
    }).inserted_id
    slack_message(msg=username + " " + 'have created weekly report at' + ' ' + str(formated_date))
    return jsonify(str(ret)), 200

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
    ret = mongo.db.reports.find_one({
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

        difficulty = request.json.get("difficulty", 0)
        rating = request.json.get("rating", 0)
        comment = request.json.get("comment", None)

        if comment is None or weekly_id is None:
            return jsonify(msg="invalid request"), 500

        juniors = get_manager_juniors(current_user['_id'])

        dab = mongo.db.reports.find({
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
            print(rap)
            for dub in rap:
                junior_name = dub['username']
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
                                "difficulty": difficulty,
                                "rating": rating,
                                "comment": comment,
                                "manager_id": str(current_user["_id"])
                            }
                        }
                    })
                    docs = mongo.db.reports.update({
                        "_id": ObjectId(weekly_id),
                        "is_reviewed": {'$elemMatch': {"_id": str(current_user["_id"]), "reviewed": False}},
                    }, {
                        "$set": {
                            "is_reviewed.$.reviewed": True
                        }})
                    dec = mongo.db.recent_activity.update({
                        "user": str(ID)},
                        {"$push": {
                            "report_reviewed": {
                                "created_at": datetime.datetime.now(),
                                "priority": 0,
                                "Message": "Your weekly report has been reviewed by "" " + manager_name
                            }}}, upsert=True)
                    slack_message(msg=junior_name + " " + 'your report is reviewed by' + ' ' + manager_name)
                    return jsonify(str(ret)), 200
                else:
                    return jsonify(msg="Already reviewed this report"), 400

        
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
            "$gte": datetime.datetime(last_monday.year, last_monday.month, last_monday.day),
            "$lte": datetime.datetime(last_sunday.year, last_sunday.month, last_sunday.day)
        }
    }).sort("created_at", 1)
    docs = [add_checkin_data(serialize_doc(doc)) for doc in docs]
    return jsonify(docs), 200

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

@bp.route('/recent_activities', methods=['GET'])
@jwt_required
def recent_activity():
    current_user = get_current_user()
    ret = mongo.db.recent_activity.find({
        "user": str(current_user['_id'])
    })
    ret = [serialize_doc(ret) for ret in ret]
    return jsonify(ret)

@bp.route('/managers_juniors', methods=['GET'])
@jwt_required
@token.manager_required
def manager_junior():
    current_user = get_current_user()
    users = mongo.db.users.find({
        "managers": {
            "$elemMatch": {"_id": str(current_user['_id'])}
        }
    })
    users = [serialize_doc(ret) for ret in users]
    return jsonify(users)

