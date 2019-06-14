from app import token
from app import mongo
from app.util import serialize_doc
from flask import (
    Blueprint,jsonify, abort, request
)
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
        })
        docs = [serialize_doc(doc) for doc in docs]
        for s_doc in docs:
            review.append(s_doc)

        doc = mongo.db.reviews_360.find({
            "user": str(current_user["_id"]),
            "anon": True
        },{"rating":1,"comment":1,"manager":1,"manager_id":1,"manager_img":1,"month":1})
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
        })
    review = [serialize_doc(doc) for doc in review]
    for doc in review:
        reviewss.append(doc)

    docss = mongo.db.reviews_360.find({
        "anon": True
    },{"rating": 1, "comment": 1, "manager": 1, "manager_id": 1, "manager_img": 1, "month": 1,"anon":1})
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
    }, {"rating": 1, "comment": 1, "manager": 1, "manager_id": 1, "manager_img": 1, "month": 1,"anon":1})
    docss = [serialize_doc(doc) for doc in docss]
    for dc in docss:
        reviewss.append(dc)
    return jsonify(reviewss)
