from flask import (
    Blueprint, g, request, abort, jsonify
)
from passlib.hash import pbkdf2_sha256

from flask_jwt_extended import (
    jwt_required, create_access_token, get_current_user
)
from bson.objectid import ObjectId

import datetime
from app.config import URL,URL_details
from app import mongo
from app.util import get_manager_profile


bp = Blueprint('auth', __name__, url_prefix='/auth')


@bp.route('/register', methods=['POST'])
def register():
   hr = mongo.db.hr.find_one({
       "integrate_with_hr": True
   })
   if hr is not None and "integrate_with_hr" in hr:
       return ('invalid request'), 500
   else:
       if not request.json:
           abort(500)
   name = request.json.get("name", None)
   username = request.json.get("username", None)
   password = request.json.get("password", None)
   if not name or not username or not password:
       return jsonify({"msg": "Invalid Request"}), 400

   user = mongo.db.users.count({
       "username": username
   })
   if user > 0:
       return jsonify({"msg": "Username already taken"}), 500

   id = mongo.db.users.insert_one({
       "name": name,
       "password": pbkdf2_sha256.hash(password),
       "username": username
   }).inserted_id
   return jsonify(str(id))



@bp.route('/login', methods=['POST'])
def login():
   hr = mongo.db.hr.find_one({
        "integrate_with_hr":True
      })
   if hr is not None and "integrate_with_hr" in hr:

       username = request.json.get("username", None)
       password = request.json.get("password", None)
       if not username:
           return jsonify(msg="Missing username parameter"), 400
       if not password:
           return jsonify(msg="Missing password parameter"), 400

       payload_user_login = {'username': username, "password": password, "action": "login", "token": None}
       response_user_token = requests.post(url=URL, json=payload_user_login)
       token = response_user_token.json()
         
       if token['data'] == {'message': 'Invalid Login'}:
           return jsonify(msg='invalid login')
       else:
           payload_user_details = {"action": "get_user_profile_detail", "token": token['data']['token']}
           response_user_details = requests.post(url=URL_details, json=payload_user_details)
           username = request.json.get("username", None)
           result = response_user_details.json()
           user_data = result['data']['user_profile_detail']
           role_response = jwt.decode(token['data']['token'], None, False)
           if role_response["role"] == "Admin":
               payload_all_user_details = {"action": "get_enable_user", "token": token['data']['token']}
               response_all_user_details = requests.post(url=URL, json=payload_all_user_details)
               result = response_all_user_details.json()
               data = result['data']
               user = mongo.db.users.insert({
                   "profile": data
               })
           else:
               pass
           role = role_response['role']
           status = user_data["status"]
           id = user_data["id"]
           name = user_data["name"]
           jobtitle = user_data["jobtitle"]
           user_Id = user_data["user_Id"]
           dob = user_data["dob"]
           gender = user_data["gender"]
           work_email = user_data["work_email"]
           slack_id = user_data["slack_id"]
           profileImage = user_data["profileImage"]

           user = mongo.db.users.count({
               "username": username})
           if user > 0:
               user = mongo.db.users.update({
                   "username": username
               }, {
                   "$set": {
                       "id": id,
                       "name": name,
                       "user_Id": user_Id,
                       "status": status,
                       "job_title": jobtitle,
                       "dob": dob,
                       "gender": gender,
                       "work_email": work_email,
                       "slack_id": slack_id,
                       "profileImage": profileImage,
                       "profile": result,
                       "role": role
                   }
               })
           else:
               user = mongo.db.users.insert_one({
                   "username": username,
                   "id": id,
                   "name": name,
                   "user_Id": user_Id,
                   "status": status,
                   "job_title": jobtitle,
                   "dob": dob,
                   "gender": gender,
                   "work_email": work_email,
                   "slack_id": slack_id,
                   "profileImage": profileImage,
                   "profile": result,
                   "role": role

               }).inserted_id
           expires = datetime.timedelta(days=1)
           access_token = create_access_token(identity=username, expires_delta=expires)
           return jsonify(access_token=access_token), 200
   else:
       if not request.json:
           abort(500)

       username = request.json.get('username', None)
       password = request.json.get('password', None)
       if not username:
           return jsonify({"msg": "Missing username parameter"}), 400
       if not password:
           return jsonify({"msg": "Missing password parameter"}), 400

       user = mongo.db.users.find_one({
           "username": username
       })
       if user is not None and "_id" in user:
           if pbkdf2_sha256.verify(password, user["password"]):
               access_token = create_access_token(identity=user)
               return jsonify(access_token=access_token), 200
           else:
               return jsonify({"msg": "invalid password"}), 500
       else:
           return jsonify({"msg": "invalid login"}), 500

    
        

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
            "_id": ObjectId(current_user["_id"],{"profile":0})
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
