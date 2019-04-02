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


@bp.route('/login', methods=['GET','POST'])
@bp.route('/login/<string:id>', methods=['PUT'])
def login(id):

    if request.method == "GET":
       username = request.json.get("username")
       password = request.json.get("password")   
       URL = 'https://hr.excellencetechnologies.in/attendance/API_HR/api.php'
       payload = {'username': username, "password": password, "action": "login", "token": None}
       response = requests.get(url=URL, json=payload)
       return jsonify(response.json())
    
    if request.method == "POST":
        URL2 = 'https://hr.excellencetechnologies.in/attendance/sal_info/api.php'
        token = request.json.get("token", None)
        payload2 = {"action": "get_user_profile_detail", "token": token}
        response = requests.post(url=URL2, json=payload2)
        user_data = response.json()
        username = request.json.get("username")
        users = mongo.db.users.insert_one({
             "profile": user_data,
             "username": username
         }).inserted_id
        user = mongo.db.users.find_one(
         {"username": username}
        )
    
        access_token = create_access_token(identity=user)
        return jsonify(access_token=access_token), 200
    

    if request.method == "PUT":
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
