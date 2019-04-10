from app import mongo
from app import token
from app.util import serialize_doc

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
    users = mongo.db.users.find({})
    users = [serialize_doc(user) for user in users]
    return jsonify(users), 200


@bp.route('/role/<string:user_id>/<string:role>', methods=['PUT'])
@jwt_required
@token.admin_required
def user_assign_role(user_id, role):
    if role == "admin" or role == "manager":
        ret = mongo.db.users.update({
            "_id": ObjectId(user_id)
        }, {
            "$set": {
                "role": role
            }
        }, upsert=False)
        return jsonify(ret), 200
    else:
        return jsonify(msg="invalid role"), 500
