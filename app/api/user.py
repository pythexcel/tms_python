from app import mongo
from app import token
from app.util import serialize_doc
import datetime

from flask import (
    Blueprint, flash, jsonify, abort, request
)

from bson.objectid import ObjectId


from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity, get_current_user, jwt_refresh_token_required,
    verify_jwt_in_request
)

bp = Blueprint('user', __name__, url_prefix='/user')


@bp.route('/list', methods=['GET'])
@jwt_required
@token.admin_required
def user_list():
    users = mongo.db.users.find({"status": "Enabled"})
    users = [serialize_doc(user) for user in users]
    return jsonify(users), 200


@bp.route('/role/<string:user_id>/<string:role>', methods=['PUT'])
@jwt_required
@token.admin_required
def user_assign_role(user_id, role):
   if role == "Admin" or role == "manager":
       ret = mongo.db.users.find_one({
           "_id": ObjectId(user_id),
           "status": "Enabled"
       })
       user_role = ret['role']
       if user_role == "Admin":
           role = "Admin"
       else:
           role = "manager"

       ret = mongo.db.users.update({
           "_id": ObjectId(user_id)
       }, {
           "$set": {
               "role": role
           }
       }, upsert=False)
       return jsonify(str(ret)), 200
   else:
       return jsonify(msg="invalid role"), 500

@bp.route('/chechkin_mandatory/<string:user_id>', methods=['PUT'])
@jwt_required
@token.admin_required
def chechkin_mandatory(user_id):
    ret = mongo.db.users.update({
        "_id": ObjectId(user_id)
    }, {
        "$set": {
            "daily_chechkin_mandatory": False
        }}, upsert=False)
    return jsonify(str(ret)), 200
    

