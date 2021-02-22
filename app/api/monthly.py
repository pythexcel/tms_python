from app import token
from app import mongo
from app.util import serialize_doc, get_manager_profile
from flask import (
    Blueprint, flash, jsonify, abort, request
)
import requests
import json
from app.config import notification_system_url,accountname
import dateutil.parser
from bson.objectid import ObjectId
from app.util import get_manager_juniors
from app.util import load_monthly_report_mesg
import datetime
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity, get_current_user, jwt_refresh_token_required,
    verify_jwt_in_request
)
from bson import json_util

bp = Blueprint('monthly', __name__, url_prefix='/')

# function for loading checkins
def load_checkin(id):
    ret = mongo.db.reports.find_one({
        "_id": ObjectId(id)
    })
    return serialize_doc(ret)

# function for loading checkins
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

# function for adding checkins
def add_checkin_data(weekly_report):
    select_days = weekly_report["select_days"]
    select_days = [load_checkin(day) for day in select_days]
    all_chekin = weekly_report['user']
    print(all_chekin)
    all_chekin = (load_all_checkin(all_chekin))

    weekly_report["select_days"] = select_days
    weekly_report['all_chekin'] = all_chekin
    return weekly_report

# function for loading kpi
def load_kpi(kpi_data):
    print(kpi_data)
    ret = mongo.db.kpi.find_one({
        "_id": ObjectId(kpi_data)
    })
    return serialize_doc(ret)

#function to add kpi data
def add_kpi_data(kpi):
    if "kpi_id" in kpi:
        data = kpi["kpi_id"]
        kpi_data = (load_kpi(data))
        kpi['kpi_id'] = kpi_data
    else:
        kpi['kpi_id'] = ""
    return kpi

# function to load all weekly data
def load_all_weekly(all_weekly):
    ret = mongo.db.reports.find({
        "user": all_weekly,
        "type": "weekly"
    })
    ret = [serialize_doc(doc) for doc in ret]
    return ret


def load_user(user):
    ret = mongo.db.users.find_one({
        "_id": ObjectId(user)
    })
    return serialize_doc(ret)

# function to add user data
def add_user_data(user):
    user_data = user['user']
    user_data = (load_user(user_data))
    user['user'] = user_data
    return user

# function for loading manager data
def load_manager(manager):
    ret = mongo.db.users.find_one({
        "_id": manager
    })
    return serialize_doc(ret)

# function for adding manager data
def add_manager_data(manager):
    for elem in manager['review']:
        elem['manager_id'] = load_manager(ObjectId(elem['manager_id']))
    return manager

# function to load details of user
def load_details(data):
    user_data = data['user']
    all_weekly = data['user']
    all_weekly = (load_all_weekly(all_weekly))
    user_data = (load_user(user_data))
    data['user'] = user_data
    if 'review' in data:
        review_detail = data['review']
    else:
        review_detail = None
    if review_detail is not None:
        for elem in review_detail:
            elem['manager_id'] = load_manager(ObjectId(elem['manager_id']))
    data['all_weekly'] = all_weekly
    return data

# function where no review will be shown to manager
def no_review(data):
    user_data = data['user']
    user_data = (load_user(user_data))
    data['user'] = user_data
    review_data = None
    data['review'] = review_data
    return data


# Api for delete monthly report
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


# Api for monthly checkin
@bp.route('/monthly', methods=["POST", "GET"])
@jwt_required
def add_monthly_checkin():
    today = datetime.datetime.utcnow()
    first = today.replace(day=1)
    lastMonth = first - datetime.timedelta(days=1)
    month = lastMonth.strftime("%B")
    current_user = get_current_user()
    slack = current_user['slack_id']
    if request.method == "GET":
        report = mongo.db.reports.find({
            "user": str(current_user["_id"]),
            "type": "monthly",
            "month": month
        })
        report = [add_user_data(serialize_doc(doc)) for doc in report]
        return jsonify(report)
    else:
        # finding weekly of the current user
        rep = mongo.db.reports.find({
            "user": str(current_user['_id']),
            "type": "weekly"
        })
        rep = [serialize_doc(doc) for doc in rep]
        if len(rep) >= 3:
            if not request.json:
                abort(500)
            report = request.json.get("report", [])
            reviewed = False
            users = mongo.db.users.find({
                "_id": ObjectId(current_user["_id"])
            })
            users = [serialize_doc(doc) for doc in users]
            managers_data = []
            # get all data of managers from current user
            for data in users:
                for mData in data['managers']:
                    mData['reviewed'] = reviewed
                    managers_data.append(mData)

            # check if report already exist don't allow user to make a new one for current month        
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
                current_user["_id"] = str(current_user["_id"])
                user = json.loads(json.dumps(current_user,default=json_util.default))
                print(user)
                monthly_payload = {"user":user,"data":None,"message_key":"monthly_notification","message_type":"simple_message"}
                notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname,json=monthly_payload)
                print(notification_message.text)
                return jsonify(str(ret)), 200
        else:
            return jsonify({"msg": "You must have atleast 3 weekly report to create a monthly report"}), 405       
        

#manager to find all their juniors monthly report
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

# managers to review their juniors monthly report
@bp.route("/manager_monthly/<string:monthly_id>", methods=["POST"])
@jwt_required
@token.manager_required
def get_manager_monthly_list(monthly_id):
    current_user = get_current_user()
    manager_name = current_user['username']
    if not request.json:
        abort(500)
    comment = request.json.get("comment", None)

    if monthly_id is None:
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
        # check if manager have given its comment or not if given don't allow to make new one else allow him
        for dub in rap:
            junior_name = dub['username']
            slack = dub['slack_id']
            email = dub['work_email']
            sap = mongo.db.reports.find({
                "_id": ObjectId(monthly_id),
                "review": {'$elemMatch': {"manager_id": str(current_user["_id"])},
                           }
            })
            sap = [serialize_doc(saps) for saps in sap]
            if not sap:
                # push the manager review in report 
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
                # in same report update the reviewed status of the manager as true if review given
                docs = mongo.db.reports.update({
                    "_id": ObjectId(monthly_id),
                    "is_reviewed": {'$elemMatch': {"_id": str(current_user["_id"]), "reviewed": False}},
                }, {
                    "$set": {
                        "is_reviewed.$.reviewed": True
                    }})
                user = json.loads(json.dumps(dub,default=json_util.default))
                monthly_reviewed_payload = {"user":user,
                "data":manager_name,"message_key":"monthly_reviewed_notification","message_type":"simple_message"}
                notification_message = requests.post(url=notification_system_url+"notify/dispatch?account-name="+accountname,json=monthly_reviewed_payload)
                return jsonify(str(ret)), 200
            else:
                return jsonify(msg="Already reviewed this report"), 400

# api for manager to delete its given response on a report within 1 hour            
@bp.route('/delete_manager_monthly_response/<string:manager_id>', methods=['DELETE'])
@jwt_required
@token.manager_required
def delete_manager_monthly_response(manager_id):
    current_user = get_current_user()
    today = datetime.datetime.utcnow()
    last_day = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
    next_day = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    # find report created between last 1 hour if found allow manager to delete its response or else not
    report = mongo.db.reports.find_one({
        "_id": ObjectId(manager_id),
        "review": {'$elemMatch': {"manager_id": str(current_user["_id"]), "created_at": {
            "$gte": last_day,
            "$lte": next_day}}
                   }})
    print(report)
    if report is not None:
        # pull the manager data from the rpeort which repsone he/she wants to delete 
        ret = mongo.db.reports.update({
            "_id": ObjectId(manager_id)}
            , {
                "$pull": {
                    "review": {
                        "manager_id": str(current_user["_id"]),
                    }
                }})
        # update his status of reviewd to false if he/she deletes his/her response
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

# function for getting manager data with review details regarding it
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

# managers to seel all their monthly report of juniors including thier profile and with COMMENT condition
@bp.route('/junior_monthly_report', methods=['GET'])
@jwt_required
@token.manager_required
def junior_monthly_report():
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

# api for manager to skip monthly report review if he is the senior most and not the only reviewer
@bp.route('/monthly_skip_review/<string:monthly_id>', methods=['POST'])
@jwt_required
@token.manager_required
def monthly_skip_review(monthly_id):
    current_user = get_current_user()
    doj = current_user['dateofjoining']
    print(doj)
    # find report of the id provided 
    reports = mongo.db.reports.find({
        "_id": ObjectId(monthly_id),
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
    # get all the join dates of manager of that report
    join_date = []
    for dates in managers:
        join_date.append(dates['dateofjoining'])
    # check that if there is only one manager do not allow him to skip review     
    if len(join_date) > 1:
        #find the oldest date of all the join date 
        oldest = min(join_date)
        # if the date is equla to current user join date let him skip review else not
        if doj == oldest:
            rep = mongo.db.reports.update({
                "_id": ObjectId(monthly_id),
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

#function for return user and managers details
def load_monthly_details(data):
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

#Api for juniors can see manager reviews.
@bp.route('/manager_monthly_response', methods=["GET"])
@jwt_required
def monthly_manager_response():
    current_user = get_current_user()
    report = mongo.db.reports.find({
        "user": str(current_user["_id"]),
        "type": "monthly",
    })
    #here call a function for monthly details
    report = [load_monthly_details(serialize_doc(doc)) for doc in report]
    if not report:
        return jsonify({"msg": "no response"}),204
    else:
        return jsonify(report)
