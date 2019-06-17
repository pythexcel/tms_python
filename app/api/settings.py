from flask import (
    Blueprint, g, request, abort, jsonify)
from app import mongo
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity, get_current_user, jwt_refresh_token_required,
    verify_jwt_in_request
)
from app import token
from bson import ObjectId

bp = Blueprint('system', __name__, url_prefix='/system')


@bp.route('/slack_settings', methods=["POST"])
@bp.route('/slack_settings/<string:id>', methods=["PUT"])
@jwt_required
@token.admin_required
def slack_setings(id):
    webhook_url = request.json.get("webhook_url", None)
    slack_token = request.json.get("slack_token", None)

    if request.method == "POST":
        ret = mongo.db.slack_tokens.insert_one({
            "webhook_url": webhook_url,
            "slack_token": slack_token
        }).inserted_id
        return jsonify(str(ret))

    if request.method == "PUT":
        ret = mongo.db.slack_tokens.update({
            "_id": ObjectId(id)
        }, {
            "$set": {
                "webhook_url": webhook_url,
                "slack_token": slack_token
            }
        }
        )
        return jsonify(str(ret))

