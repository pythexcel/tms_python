from flask import (
    Blueprint, g, request, abort, jsonify
)
from passlib.hash import pbkdf2_sha256

from flask_jwt_extended import (
    jwt_required, create_access_token, get_current_user
)
from bson.objectid import ObjectId

import datetime

from app import mongo
from app.util import get_manager_profile


bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/login', methods=['POST'])
def login():
    if not request.json:
        abort(500)
    URL = 'https://hr.excellencetechnologies.in/attendance/API_HR/api.php'
    username = request.json.get("username", None)
    password = request.json.get("password", None)
    if not username:
        return jsonify(msg="Missing username parameter"), 400
    if not password:
        return jsonify(msg="Missing password parameter"), 400
    
   
    payload = {'username': username, "password": password, "action": "login", "token": None}
    response = requests.post(url=URL, json=payload)
    token = response.json()
    if response is not None:
        URL2 = 'https://hr.excellencetechnologies.in/attendance/sal_info/api.php'
        payload2 = {"action": "get_user_profile_detail", "token": token['data']['token']}
        response2 = requests.post(url=URL2, json=payload2)
        username = request.json.get("username", None)
        result = response2.json()
        user = mongo.db.users.count({
            "username": username})
        if user > 0:
                return jsonify({"msg": "Username already taken"}), 500

        user = mongo.db.users.insert_one({
            "profile": result,
           "username": username
        }).inserted_id
        
        if username is not None:
            access_token = create_access_token(identity=username)
            return jsonify(access_token=access_token), 200
        else:
            return jsonify(msg="invalid password"),500  
    else:
        return jsonify(msg="invalid login"), 500


@bp.route('/update_profile/<string:id>', methods=['PUT'])
@jwt_required
@token.admin_required
def update_profile(id):

    ret = mongo.db.users.update({
        "_id": ObjectId(id)
        }, {
        "$set": {
            "profile": request.json
        }
        })
    return jsonify(ret), 200


@bp.route('/ping', methods=['GET'])
def ping():
    return "pong"

# Protect a view with jwt_required, which requires a valid access token
# in the request to access.
@bp.route('/protected', methods=['GET'])
@jwt_required
def protected():
    # get_token()
    current_user = get_current_user()
    return jsonify(logged_in_as=current_user["username"]), 200


@bp.route('/profile', methods=['PUT', 'GET'])
@jwt_required
def profile():
    current_user = get_current_user()
    if request.method == "GET":
        ret = mongo.db.users.find_one({
            "_id": ObjectId(current_user["_id"])
        })
        ret["_id"] = str(ret["_id"])
        if "kpi_id" in ret and ret["kpi_id"] is not None:
            ret_kpi = mongo.db.kpi.find_one({
                "_id": ObjectId(ret["kpi_id"])
            })
            ret_kpi["_id"] = str(ret_kpi['_id'])
            ret['kpi'] = ret_kpi
        else:
            ret['kpi'] = {}

        if "managers" in ret:
            ret["managers"] = [get_manager_profile(
                manager) for manager in ret['managers']]
        else:
            ret["managers"] = []
        return jsonify(ret)
    if request.json is None:
        abort(500)

    ret = mongo.db.users.update({
        "_id": ObjectId(current_user["_id"])
    }, {
        "$set": {
            "profile": request.json
        }
    })
    return jsonify(ret), 200
