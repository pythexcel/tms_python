from flask import (
   Blueprint, g, request, abort, jsonify)
from app import mongo


bp = Blueprint('system', __name__, url_prefix='/system')


@bp.route('/settings', methods=['POST'])
def settings():
 if not request.json:
     abort(500)
 integrate_with_hr = request.json.get('integrate_with_hr', False)
 hr = mongo.db.hr.count({
     "integrate_with_hr": integrate_with_hr})

 if hr > 0:
     hr = mongo.db.hr.update({
         "integrate_with_hr": integrate_with_hr
     }, {
                 "$unset": {
                     "integrate_with_hr": integrate_with_hr
                 }
             })
     return ("")
 else:
      hr = mongo.db.hr.insert_one({
         "integrate_with_hr": integrate_with_hr
      }).inserted_id
 return jsonify(str(hr))
