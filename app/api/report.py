from app import token
from app import mongo
from app.util import serialize_doc, get_manager_profile
from flask import (
    Blueprint, flash, jsonify, abort, request
)

from bson.objectid import ObjectId
import dateutil.parser
from app.util import slack_message, slack_msg
from app.config import slack_token
from slackclient import SlackClient
import requests
from app.config import attn_url,secret_key

import datetime


from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity, get_current_user, jwt_refresh_token_required,
    verify_jwt_in_request
)

bp = Blueprint('report', __name__, url_prefix='/')

@bp.route('/slack', methods=["GET"])
@jwt_required
def slack():
    current_user = get_current_user()
    slack = current_user['slack_id']
    slack_id = SlackClient(slack_token)
    data = slack_id.api_call(
        "groups.list"
    )
    element = data['groups']
    channels = []
    for ret in element:
        if slack in ret['members']:
            channels.append({'value': ret['id'], 'text': ret['name']})
    return jsonify(channels)


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
            slack_msg(channel=slackChannels,
                      msg="<@"+slack+">!" + "\n" + "Report: " + "_" + report + "_" + "\n"
                          + "Highlight: " + highlight)
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
            slack_message(msg="<@"+slack+">!"+' ''have created daily chechk-in at'+' '+str(formatted_date))
            slack_msg(channel=slackChannels,
                      msg="<@"+slack+">!" + "\n" + "Report: " + "_" + report + "_" + "\n"
                          + "Highlight: " + highlight)
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
    extra = request.json.get("extra", "")
    select_days = request.json.get("select_days", [])
    difficulty = request.json.get("difficulty", 0)
    username = current_user['username']
    slack = current_user['slack_id']
 
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
        
    managers_name = []
    for elem in managers_data:
        managers_name.append({"Id":elem['_id']})    
    
    ret = mongo.db.reports.insert_one({
        "k_highlight": k_highlight,
        "extra": extra,
        "select_days": select_days,
        "user": str(current_user["_id"]),
        #"username": username,
        "created_at": datetime.datetime.utcnow(),
        "type": "weekly",
        "is_reviewed": managers_data,
        "cron_checkin": True,
        "cron_review_activity": False,
        "kpi_json": kpi_name,
        "era_json": era_name,
        "difficulty": difficulty
    }).inserted_id

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

    slack_message(msg="<@"+slack+">!"+' ''have created weekly report at' + ' ' + str(formated_date))
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


def load_all_checkin(all_chekin):
    today = datetime.datetime.utcnow()
    last_monday = today - datetime.timedelta(days=(today.weekday() + 8))
    ret = mongo.db.reports.find({
        "user": all_chekin,
        "type": "daily",
        "created_at": {
            "$gte": datetime.datetime(last_monday.year, last_monday.month, last_monday.day)}
    })
    ret = [serialize_doc(doc) for doc in ret]
    return ret


def add_checkin_data(weekly_report):
    select_days = weekly_report["select_days"]
    select_days = [load_checkin(day) for day in select_days]
    all_chekin = weekly_report['user']
    all_chekin = (load_all_checkin(all_chekin))
    weekly_report["select_days"] = select_days
    weekly_report['all_chekin'] = all_chekin
    return weekly_report

@bp.route("/manager_weekly_all", methods=["GET"])
@jwt_required
@token.manager_required
def get_manager_weekly_list_all():
    today = datetime.datetime.utcnow()
    last_monday = today - datetime.timedelta(days=today.weekday())
    current_user = get_current_user()
    juniors = get_manager_juniors(current_user['_id'])
    docs = mongo.db.reports.find({
        "type": "weekly",
        "user": {
            "$in": juniors
        },
        "created_at": {
            "$gte": datetime.datetime(last_monday.year, last_monday.month, last_monday.day)}
    }).sort("created_at", 1)
    docs = [add_checkin_data(serialize_doc(doc)) for doc in docs]
    return jsonify(docs), 200


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

        difficulty = request.json.get("difficulty", 0)
        rating = request.json.get("rating", 0)
        comment = request.json.get("comment", None)

        if comment is None or weekly_id is None:
            return jsonify(msg="invalid request"), 500
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
                junior_name = dub['username']
                slack = dub['slack_id']
                print(slack)
                manager = dub['managers']
                for a in manager:
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
                                        "difficulty": difficulty,
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
                            slack_message(msg="Hi"+' '+"<@"+slack+">!"+' ' + "your report is reviewed by" + ' ' + manager_name)
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
            "$gte": datetime.datetime(last_monday.year, last_monday.month, last_monday.day)
            
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
def reviews_360():
    today = datetime.datetime.utcnow()
    month = today.strftime("%B")
    current_user = get_current_user()
    if request.method == "GET":

        review = []
        docs = mongo.db.reviews_360.find({
            "user": str(current_user["_id"]),
            "anon": False
        })
        docs = [serialize_doc(doc) for doc in docs]
        for s_doc in docs:
            review.append(s_doc)

        doc = mongo.db.reviews_360.find({
            "user": str(current_user["_id"]),
            "anon": True
        }, {"rating": 1, "comment": 1, "manager": 1, "manager_id": 1, "manager_img": 1, "month": 1})
        doc = [serialize_doc(doc) for doc in doc]
        for single_d in doc:
            review.append(single_d)
        return jsonify(review)
    if not request.json:
        abort(500)
    manager = request.json.get("manager", None)
    manager_id = request.json.get("managerID")
    manager_image = request.json.get("managerProfileImage")
    rating = request.json.get("rating", None)
    comment = request.json.get("comment", "")
    anon = request.json.get("anon", True)
    user = str(current_user["_id"])
    username = current_user["username"]
    profileImage = current_user["profileImage"]
    if manager is None or rating is None:
        abort(500)
    if anon == 0:
        anon = False
    else:
        anon = True
    rep = mongo.db.reviews_360.find_one({
        "user": str(user),
        "month": month,
        "manager_id": manager_id
    })

    if rep is not None:
        return jsonify(
            {"msg": "You have already posted review against this manager for this month, try again next month"}), 409
    else:
        ret = mongo.db.reviews_360.insert_one({
            "manager": manager,
            "manager_id": manager_id,
            "manager_img": manager_image,
            "rating": rating,
            "comment": comment,
            "anon": anon,
            "user": user,
            "month": month,
            "username": username,
            "profileImage": profileImage
        }).inserted_id
        return jsonify(str(ret))
    
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
    }, {"profile": 0}).sort("created_at", 1)
    users = [add_kpi_data(serialize_doc(ret)) for ret in users]
    return jsonify(users)


def load_user(user):
    ret = mongo.db.users.find_one({
        "_id": ObjectId(user)
    },{"profile": 0})
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
    }, {"profile": 0})
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
    },{"profile": 0})
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
    if data['review'] is None:
        review_detail = None
    else:
        review_detail = data['review']
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
    }, {"profile": 0})
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
    
    
#Api for delete monthly report
@bp.route('/delete_monthly/<string:monthly_id>', methods=['DELETE'])
@jwt_required
def delete_monthly(monthly_id):
   current_user = get_current_user()
   docs = mongo.db.reports.remove({
       "_id": ObjectId(monthly_id),
       "type": "monthly",
       "user": str(current_user['_id'])
   })
   return jsonify(str(docs)), 200


#Api for monthly checkin
@bp.route('/monthly', methods=["POST", "GET"])
@jwt_required
def add_monthly_checkin():
    today = datetime.datetime.utcnow()
    month = today.strftime("%B")
    current_user = get_current_user()
    doj = current_user['dateofjoining']
    date = datetime.datetime.strptime(doj, "%Y-%m-%d %H:%M:%S")
    datee = date.day
    if request.method == "GET":
        report = mongo.db.reports.find({
            "user": str(current_user["_id"]),
            "type": "monthly",
            "month": month
        })
        report = [add_user_data(serialize_doc(doc)) for doc in report]
        return jsonify(report)
    else:
        if datee > 7:
            join_date = datee - 7
        else:
            join_date = datee

        print(join_date)
        today_date = int(today.strftime("%d"))
        print(today_date)
        if today_date > join_date:
            if not request.json:
                abort(500)
            report = request.json.get("report", [])
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
            rep = mongo.db.reports.find_one({
                "user": str(current_user["_id"]),
                "type": "monthly",
                "month": month,
            })
            if rep is not None:
                return jsonify({"msg": "You have already submitted your monthly report"}), 409
            else:
                ret = mongo.db.reports.insert_one({
                    "user": str(current_user["_id"]),
                    "created_at": datetime.datetime.utcnow(),
                    "type": "monthly",
                    "is_reviewed": managers_data,
                    "report": report,
                    "month": month
                }).inserted_id
                return jsonify(str(ret)), 200
        else:
            return jsonify({"msg": "Your date of joining was on" + str(datee) + "you can only submit monthly report 7 "
                                                                                "days before your joining date "}), 404


@bp.route("/manager_monthly_all", methods=["GET"])
@jwt_required
@token.manager_required
def get_manager_monthly_list_all():
   current_user = get_current_user()
   juniors = get_manager_juniors(current_user['_id'])
   print(juniors)
   docs = mongo.db.reports.find({
       "type": "monthly",
       "user": {
           "$in": juniors
       }
   }).sort("created_at", 1)
   docs = [load_details(serialize_doc(doc)) for doc in docs]
   return jsonify(docs), 200


@bp.route("/manager_monthly/<string:monthly_id>", methods=["POST"])
@jwt_required
@token.manager_required
def get_manager_monthly_list(monthly_id):
    current_user = get_current_user()
    manager_name = current_user['username']
    if not request.json:
        abort(500)
    comment = request.json.get("comment", None)

    if comment is None or monthly_id is None:
        return jsonify(msg="invalid request"), 500
    juniors = get_manager_juniors(current_user['_id'])

    dab = mongo.db.reports.find({
        "_id": ObjectId(monthly_id),
        "type": "monthly",
        "is_reviewed": {'$elemMatch': {"_id": str(current_user["_id"]), "reviewed": False}},
        "user": {
            "$in": juniors
        }
    }).sort("created_at", 1)
    dab = [serialize_doc(doc) for doc in dab]
    for data in dab:
        ID = data['user']
        rap = mongo.db.users.find({
            "_id": ObjectId(str(ID))
        })
        rap = [serialize_doc(doc) for doc in rap]
        for dub in rap:
            junior_name = dub['username']
            sap = mongo.db.reports.find({
                "_id": ObjectId(monthly_id),
                "review": {'$elemMatch': {"manager_id": str(current_user["_id"])},
                           }
            })
            sap = [serialize_doc(saps) for saps in sap]
            if not sap:
                ret = mongo.db.reports.update({
                    "_id": ObjectId(monthly_id)
                }, {
                    "$push": {
                        "review": {
                            "created_at": datetime.datetime.utcnow(),
                            "comment": comment,
                            "manager_id": str(current_user["_id"])
                        }
                    }
                })
                docs = mongo.db.reports.update({
                    "_id": ObjectId(monthly_id),
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
                            "Message": "Your monthly report has been reviewed by "" " + manager_name
                        }}}, upsert=True)
                slack_message(msg=junior_name + " " + 'your monthly report is reviewed by' + ' ' + manager_name)
                return jsonify(str(ret)), 200
            else:
                return jsonify(msg="Already reviewed this report"), 400

    
@bp.route('/skip_review/<string:weekly_id>', methods=['POST'])
@jwt_required
@token.manager_required
def skip_review(weekly_id):
    current_user = get_current_user()
    doj = current_user['dateofjoining']
    print(doj)
    reports = mongo.db.reports.find({
        "_id": ObjectId(weekly_id),
        "is_reviewed": {'$elemMatch': {"_id": str(current_user["_id"])}
        }
    })
    reports = [serialize_doc(doc) for doc in reports]
    manager_id = []
    for data in reports:
        for elem in data['is_reviewed']:
            manager_id.append(ObjectId(elem['_id']))
    managers = mongo.db.users.find({
        "_id": {"$in": manager_id}
    })
    managers = [serialize_doc(doc) for doc in managers]
    join_date = []
    for dates in managers:
        join_date.append(dates['dateofjoining'])
    if len(join_date) > 1:
        oldest = min(join_date)
        if doj == oldest:
            rep = mongo.db.reports.update({
                "_id": ObjectId(weekly_id),
                "is_reviewed": {'$elemMatch': {"_id": str(current_user["_id"])}},
            }, {
                "$pull": {
                    "is_reviewed": {"_id": str(current_user["_id"])}
                }}, upsert=False)
            return jsonify(str(rep))
        else:
            return jsonify({"msg": "You cannot skip this report review"}), 400
    else:
        return jsonify({"msg": "You cannot skip this report review as you are the only manager"}), 400

@bp.route('/delete_manager_monthly_response/<string:manager_id>', methods=['DELETE'])
@jwt_required
@token.manager_required
def delete_manager_monthly_response(manager_id):
    current_user = get_current_user()
    today = datetime.datetime.utcnow()
    last_day = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
    next_day = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    report = mongo.db.reports.find_one({
        "_id": ObjectId(manager_id),
        "review": {'$elemMatch': {"manager_id": str(current_user["_id"]), "created_at": {
                    "$gte": last_day,
                    "$lte": next_day}}
        }})
    print(report)
    if report is not None:
        ret = mongo.db.reports.update({
            "_id": ObjectId(manager_id)}
            , {
            "$pull": {
                "review": {
                    "manager_id": str(current_user["_id"]),
                    }
            }})
        docs = mongo.db.reports.update({
            "_id": ObjectId(manager_id),
            "is_reviewed": {'$elemMatch': {"_id": str(current_user["_id"]), "reviewed": True}},
        }, {
            "$set": {
                "is_reviewed.$.reviewed": False
            }})
        return jsonify(str(docs)), 200
    else:
        return jsonify({"msg": "You can no longer delete your submitted report"}), 400
def details_manager(data):
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



@bp.route('/junior_monthly_report', methods=['GET'])
@jwt_required
@token.manager_required
def junior_monthly_report():
    current_user = get_current_user()
    users = mongo.db.users.find({
        "managers": {
            "$elemMatch": {"_id": str(current_user['_id'])}
        }
    }, {"profile": 0})
    users = [serialize_doc(ret) for ret in users]
    ID = []
    for data in users:
        ID.append(data['_id'])
    print(ID)
    reports = mongo.db.reports.find({
        "user": {"$in": ID},
        "type": "monthly",
        "is_reviewed": {'$elemMatch': {"_id": str(current_user["_id"]), "reviewed": False}}
    }).sort("created_at", 1)
    reports = [no_review(serialize_doc(doc)) for doc in reports]
    report = mongo.db.reports.find({
        "user": {"$in": ID},
        "type": "monthly",
        "is_reviewed": {'$elemMatch': {"_id": str(current_user["_id"]), "reviewed": True}}
    }).sort("created_at", 1)
    report = [details_manager(serialize_doc(doc)) for doc in report]
    report_all = reports + report

    return jsonify(report_all)

@bp.route('/get_managers', methods=['GET'])
@jwt_required
def get_managers():
    current_user = get_current_user()
    managers = current_user["managers"]
    if not managers:
        return jsonify(
            {"msg": "currently you don't have any manager assigned"}), 409
    else:
        return jsonify(managers)

@bp.route("/360_get_juniors_reviews", methods=["GET"])
@jwt_required
@token.manager_required
def get_juniors_reviews():
    current_user = get_current_user()
    id = str(current_user['_id'])
    reviewss = []
    reviews = mongo.db.reviews_360.find({
        "manager_id": id,
        "anon": False
    })
    reviews = [serialize_doc(doc) for doc in reviews]
    for doc in reviews:
        reviewss.append(doc)

    docss = mongo.db.reviews_360.find({
        "manager_id": id,
        "anon": True
    }, {"rating": 1, "comment": 1, "manager": 1, "manager_id": 1, "manager_img": 1, "month": 1,"anon":1})
    docss = [serialize_doc(doc) for doc in docss]
    for dc in docss:
        reviewss.append(dc)
    return jsonify(reviewss)


@bp.route("/admin_get_reviews", methods=["GET"])
@jwt_required
@token.admin_required
def get_reviews():
    reviewss = []
    review = mongo.db.reviews_360.find({
        "anon": False
    })
    review = [serialize_doc(doc) for doc in review]
    for doc in review:
        reviewss.append(doc)

    docss = mongo.db.reviews_360.find({
        "anon": True
    }, {"rating": 1, "comment": 1, "manager": 1, "manager_id": 1, "manager_img": 1, "month": 1,"anon":1})
    docss = [serialize_doc(doc) for doc in docss]
    for dc in docss:
        reviewss.append(dc)
    print(reviewss)
    return jsonify(reviewss)

