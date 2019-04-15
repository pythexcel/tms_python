from flask import (
   Blueprint, g, request, abort, jsonify)
from app import mongo
from flask_jwt_extended import (
    jwt_required, create_access_token, get_current_user
)


bp = Blueprint('system', __name__, url_prefix='/system')


@bp.route('/settings', methods=['POST'])
@jwt_required
def settings():
 user = get_current_user()

 if user["role"] == "Admin":   
    if not request.json:
        abort(500)
    integrate_with_hr = request.json.get('integrate_with_hr', False)
    if integrate_with_hr is True:
        hr = mongo.db.hr.insert_one({
            "integrate_with_hr": integrate_with_hr
        }).inserted_id
        return jsonify(str(hr))
    else:
        hr = mongo.db.hr.update({
            "integrate_with_hr": True
        }, {
                "$unset": {
                     "integrate_with_hr": integrate_with_hr
                 }
             })
        return ("settings off")
