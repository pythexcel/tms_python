from app import token
from app import mongo
from flask import (
    Blueprint, flash, jsonify, abort, request
)

from bson.objectid import ObjectId
from app.util import serialize_doc,get_manager_juniors
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity, get_current_user, jwt_refresh_token_required,
    verify_jwt_in_request
)

bp = Blueprint('kpi', __name__, url_prefix='/kpi')


@bp.route('', methods=['POST', 'GET'])
@bp.route('/<string:id>', methods=['PUT', 'DELETE'])
@jwt_required
@token.admin_required
def kpi(id=None):
    if request.method == "GET":
        docs = mongo.db.kpi.find({})
        kpis = []
        for doc in docs:
            doc["_id"] = str(doc["_id"])
            kpis.append(doc)
        return jsonify(kpis), 200

    if request.method == "DELETE":
       kpi = mongo.db.kpi.remove({
           "_id": ObjectId(id)
       })
       return jsonify(str(kpi)), 200

    if not request.json:
        abort(500)
    kpi_name = request.json.get('kpi_name', None)
    kpi_json = request.json.get('kpi_json', None)
    era_json = request.json.get('era_json', None)

    if kpi_json is None or kpi_name is None:
        return jsonify(msg="Invalid request"), 400

    if request.method == "POST":
        kpi = mongo.db.kpi.insert_one({
            "kpi_name": kpi_name,
            "kpi_json": kpi_json,
            "era_json": era_json
        })
        return jsonify(str(kpi.inserted_id)), 200
    elif request.method == "PUT":
        if id is None:
            return jsonify(msg="Invalid request"), 400

        kpi = mongo.db.kpi.update({
            "_id": ObjectId(id)
        },
            {
            "$set": {
                "kpi_name": kpi_name,
                "kpi_json": kpi_json,
                "era_json": era_json
            }
        })

        return jsonify(str(kpi)), 200


@bp.route("/assign_kpi/<string:user_id>/<string:kpi_id>", methods=["GET"])
@jwt_required
@token.admin_required
def assign_kpi_to_user(user_id, kpi_id):
    if kpi_id == str(-1):
        ret = mongo.db.users.update({
            "_id": ObjectId(user_id),
            "status": "Enabled"
        }, {
            "$unset": {
                "kpi_id": ""
            }
        })
    else:
        ret = mongo.db.users.update({
            "_id": ObjectId(user_id)
        }, {
            "$set": {
                "kpi_id": kpi_id
            }
        })
    return jsonify(str(ret)), 200


@bp.route('/users_on_kpi/<string:kpi_id>', methods=["GET"])
@jwt_required
@token.admin_required
def memeber_kpi(kpi_id):
    users = mongo.db.users.find({
        "kpi_id": kpi_id,
        "status": "Enabled"
    }, {"password": 0})
    users = [serialize_doc(user) for user in users]
    return jsonify(users)


@bp.route("/assign_manager/<string:user_id>/<string:manager_id>/<int:weight>", methods=["GET"])
@jwt_required
@token.admin_required
def assign_manager(user_id, manager_id, weight):
    if weight > 0:
        manage = mongo.db.users.find_one({
            "_id": ObjectId(manager_id),
            "status": "Enabled"
        })
        username =manage['username']
        job_title = manage['jobtitle']
        if 'profileImage' in manage:
            profileImage = manage['profileImage']
        else:
            profileImage = ""    

        if "role" in manage and (manage["role"] == "manager" or manage["role"] == "Admin"):
            ret = mongo.db.users.update({
                "_id": ObjectId(user_id)
            }, {
                "$pull": {
                    "managers": {
                        "_id": manager_id
                    }
                }
            })
            ret = mongo.db.users.update({
                "_id": ObjectId(user_id)
            }, {
                "$push": {
                    "managers": {
                        "_id": manager_id,
                        "weight": weight,
                        "username": username,
                        "job_title": job_title,
                        "profileImage": profileImage
                    }
                }
            })
        else:
            return jsonify(msg="user should be a manger"), 500
    else:
        ret = mongo.db.users.update({
            "_id": ObjectId(user_id)
        }, {
            "$pull": {
                "managers": {
                    "_id": manager_id
                }
            }
        })
        check = get_manager_juniors(manager_id)
        if not check:
            ret = mongo.db.users.update({
                "_id": ObjectId(manager_id)
            }, {
                "$set": {
                    "role":"Employee"
                }
            })
        else:
            pass
    return jsonify(str(ret)), 200


