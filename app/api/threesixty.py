from app import token
from app import mongo
from app.util import serialize_doc
from flask import (
    Blueprint,jsonify, abort, request
)
from bson.objectid import ObjectId
import datetime
from flask_jwt_extended import (jwt_required, get_current_user
)




bp = Blueprint('threesixty', __name__, url_prefix='/')

@bp.route('/get_managers', methods=['GET'])
@jwt_required
def get_managers():
    current_user = get_current_user()
    managers = current_user["managers"]
    if not managers:
        return jsonify(
            {"msg": "currently you don't have any manager assigned"}),204
    else:
        return jsonify(managers)

#-----------------------------------------------------------------------------------------------------------



@bp.route("/360_reviews", methods=["GET", "POST"])
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
        }).sort("month", 1)
        docs = [serialize_doc(doc) for doc in docs]
        for s_doc in docs:
            review.append(s_doc)

        doc = mongo.db.reviews_360.find({
            "user": str(current_user["_id"]),
            "anon": True
        },{"username":0,"user":0,"profileImage":0}).sort("month", 1)
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
        anon =False
    else:
        anon = True
    rep = mongo.db.reviews_360.find_one({
        "user": str(user),
        "month": month,
        "manager_id": manager_id
    })
    if rep is not None:
        return jsonify({"msg": "You have already posted review against this manager for this month, try again next month"}),204
    else:
        ret = mongo.db.reviews_360.insert_one({
            "manager":manager,
            "manager_id":manager_id,
            "manager_img":manager_image,
            "rating": rating,
            "comment": comment,
            "anon": anon,
            "seen_id":manager_id,
            "user": user,
            "month":month,
            "username": username,
            "profileImage":profileImage
        }).inserted_id
        return jsonify(str(ret))



#Api For Admin can see all reviews
@bp.route("/admin_get_reviews", methods=["GET"])
@jwt_required
@token.admin_required
def get_reviews():
    reviewss = [ ]
    review = mongo.db.reviews_360.find({
        "anon": False
        }).sort("month", 1)
    review = [serialize_doc(doc) for doc in review]
    for doc in review:
        reviewss.append(doc)

    docss = mongo.db.reviews_360.find({
        "anon": True
    },{"username":0,"user":0,"profileImage":0}).sort("month", 1)
    docss=[serialize_doc(doc) for doc in docss]
    for dc in docss:
        reviewss.append(dc)
    return jsonify(reviewss)


#Manager can see his junior reviews
@bp.route("/360_get_juniors_reviews", methods=["GET"])
@jwt_required
@token.manager_required
def get_juniors_reviews():
    current_user = get_current_user()
    id = str(current_user['_id'])
    reviewss = [ ]
    reviews = mongo.db.reviews_360.find({
        "manager_id":id,
        "anon":False
    })
    reviews = [serialize_doc(doc) for doc in reviews]
    for doc in reviews:
        reviewss.append(doc)

    docss = mongo.db.reviews_360.find({
        "manager_id": id,
        "anon": True
    }, {"username":0,"user":0,"profileImage":0})
    docss = [serialize_doc(doc) for doc in docss]
    for dc in docss:
        reviewss.append(dc)
    return jsonify(reviewss)


@bp.route("/360_updates/<string:id>", methods=["PUT"])
@jwt_required
@token.manager_required
def update_seen(id):
    ret = mongo.db.reviews_360.update({
        "_id": ObjectId(id)
    }, {
        "$set": {
            "seen_id":None
            }
        }
    )
    return jsonify(str(ret))

#Api for check if review_mandatory is on or user have submited his 360 review to manager.
@bp.route("/360_review_mandatory", methods=["GET"])
@jwt_required
def review_mandatory():
    today = datetime.datetime.utcnow()
    month = today.strftime("%B")
    current_user = get_current_user()
    state = mongo.db.schdulers_setting.find_one({
        "revew_360_setting": {"$exists": True}
    }, {"revew_360_setting": 1, '_id': 0})
    status = state['revew_360_setting']
    if status==1:
        reviews = mongo.db.reviews_360.find_one({
        "username":current_user["username"],
        "month":month
        })
        if not reviews:
            return jsonify({"is_reviwed":False})
        else:
            return jsonify({"is_reviwed":True})
    else:
        return jsonify({"is_reviwed":True})



#Api for find same KPI members
@bp.route("/Same_kpi_members", methods=["GET"])
@jwt_required
def Same_kpi_members():
    current_user = get_current_user()
    kpi_id=current_user["kpi_id"]
    _id=current_user["_id"]
    revie = mongo.db.users.find({
        "kpi_id":kpi_id,
        })
    revie = [serialize_doc(doc) for doc in revie]    
    return jsonify(revie)


#Api for submit review against same kpi members or get review from same kpi members.
@bp.route("/Same_kpi_reviews", methods=["POST","GET"])
@jwt_required
def Same_kpi_reviews():
    current_user = get_current_user()
    today = datetime.datetime.utcnow()
    month = today.strftime("%B")
    
    if request.method == "GET":
        rev = mongo.db.peer_to_peer.find({
        "user_id":str(current_user["_id"]),
        "month":month
        })
        rev = [serialize_doc(doc) for doc in rev]
        return jsonify(rev)

    if request.method == "POST":
        comment = request.json.get("comment", None)
        user_id = request.json.get("user_id", None)
        ret = mongo.db.peer_to_peer.insert_one({
            "comment":comment,
            "month":month,
            "created_at": today,
            "kpi_id":current_user['kpi_id'],
            "reviewer_id":str(current_user['_id']),
            "user_id":user_id
        }).inserted_id
        return jsonify(str(ret))



#Api for get review which current user submit to others
@bp.route("/Same_kpi_self_reviews", methods=["GET"])
@jwt_required
def Same_kpi_self_reviews():
    current_user = get_current_user()
    today = datetime.datetime.utcnow()
    month = today.strftime("%B")

    rev = mongo.db.peer_to_peer.find({
        "reviewer_id":str(current_user["_id"]),
        "month":month
        })
    rev = [serialize_doc(doc) for doc in rev]
    return jsonify(rev)


@bp.route('/delete_peer_report/<string:report_id>', methods=['DELETE'])
@jwt_required
def delete_peer_report(report_id):
    current_user = get_current_user()
    today = datetime.datetime.utcnow()
    last_day = datetime.datetime.utcnow() - datetime.timedelta(minutes=30)
    print(last_day)
    print(today)
    report = mongo.db.peer_to_peer.find_one({
        "_id": ObjectId(report_id),
        "created_at": {"$gte": last_day}
            })

    if report:
        docs = mongo.db.peer_to_peer.remove({
            "_id": ObjectId(report_id),
            "reviewer_id": str(current_user['_id']),
        })
        return jsonify(str(docs)), 200
    else:
        return jsonify({"msg": "You can not delete review after 30 minutes"}),403


