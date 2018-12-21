from flask import Flask, jsonify, abort, request, make_response

from functools import wraps

from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity, get_current_user, jwt_refresh_token_required,
    verify_jwt_in_request
)
from bson.objectid import ObjectId

from flask_restful import Resource, Api

from flask_pymongo import PyMongo

from passlib.hash import pbkdf2_sha256

from flask_cors import CORS


import datetime


app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/test_db_manish"
mongo = PyMongo(app)
api = Api(app)
CORS(app)


app.config['JWT_SECRET_KEY'] = 'xxxx'  # Change this!
jwt = JWTManager(app)

# tasks = [
#     {
#         'id': 1,
#         'title': 'Buy groceries',
#         'description': 'Milk, Cheese, Pizza, Fruit, Tylenol',
#         'done': False
#     },
#     {
#         'id': 2,
#         'title': 'Learn Python',
#         'description': 'Need to find a good Python tutorial on the web',
#         'done': False
#     }
# ]


# @app.route('/todo/tasks', methods=['GET'])
# def get_tasks():
#     return jsonify({'tasks': tasks})


# @app.route('/todo/tasks/<int:task_id>', methods=['GET'])
# def get_task(task_id):
#     task = [task for task in tasks if task['id'] == task_id]
#     if len(task) == 0:
#         abort(400)
#     return jsonify(task)


# @app.route("/todo/tasks", methods=['POST'])
# def add_task():
#     if not request.json or not'title' in request.json:
#         abort(500, "Invalid Request")

#     tasks.append({
#         "id": len(tasks) + 1,
#         "title": request.json["title"],
#         "description": "",
#         "done": False
#     })
#     return jsonify(True)


# @app.route("/todo/tasks/<int:task_id>", methods=["DELETE"])
# def delete_task(task_id):
#     if not task_id:
#         abort(500, "Task ID is required for delete")
#     global tasks
#     tasks = [task for task in tasks if task['id'] != task_id]
#     return jsonify(True)


# def update(task, task_id, data):
#     if task["id"] == task_id:
#         if 'title' in data:
#             task["title"] = data['title']
#         if 'description' in data:
#             task["description"] = data["description"]
#     return task


# @app.route("/todo/tasks/<int:task_id>", methods=["PUT"])
# def edit_task(task_id):
#     if not request.json:
#         abort(500, "Invalid Request")
#     global tasks
#     tasks = [update(task, task_id, request.json) for task in tasks]
#     return jsonify(tasks)


@app.errorhandler(400)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 400)


@app.errorhandler(500)
def error_500(error):
    return make_response({}, 500)


@jwt.user_identity_loader
def user_identity_lookup(user):
    return str(user["_id"])


@jwt.user_loader_callback_loader
def user_loader_callback(identity):
    user = mongo.db.users.find_one({
        "_id": ObjectId(identity)
    })
    if user is None or "_id" not in user:
        return None
    user["_id"] = str(user["_id"])
    return user


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user = get_current_user()

        if user["username"] == "manish2":
            return fn(*args, **kwargs)

        if 'role' in user:
            if user['role'] != 'admin':
                return jsonify(msg='Admins only!'), 403
            else:
                return fn(*args, **kwargs)
        return jsonify(msg='Admins only!'), 403
    return wrapper


def manager_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user = get_current_user()
        if 'role' in user:
            if user['role'] == 'manager' or user['role'] == 'admin':
                return fn(*args, **kwargs)
            else:
                return jsonify(msg='manager only!'), 403
        return jsonify(msg='manager only!'), 403
    return wrapper


@app.route('/register', methods=['POST'])
def register():
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


@app.route('/login', methods=['POST'])
def login():
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


# Protect a view with jwt_required, which requires a valid access token
# in the request to access.
@app.route('/protected', methods=['GET'])
@jwt_required
def protected():
    current_user = get_current_user()
    return jsonify(logged_in_as=current_user["username"]), 200


@app.route('/kpi', methods=['POST', 'GET'])
@app.route('/kpi/<string:id>', methods=['PUT', 'DELETE'])
@jwt_required
@admin_required
def kpi(id=None):
    if request.method == "GET":
        docs = mongo.db.kpi.find({})
        kpis = []
        for doc in docs:
            doc["_id"] = str(doc["_id"])
            kpis.append(doc)
        return jsonify(kpis), 200

    if request.method == "DELETE":
        return jsonify(mongo.db.kpi.remove({
            "_id": ObjectId(id)
        }))

    if not request.json:
        abort(500)

    kpi_name = request.json.get('kpi_name', None)
    kpi_json = request.json.get('kpi_json', None)
    kra_json = request.json.get('kra_json', None)

    if kpi_json is None or kpi_name is None:
        return jsonify({"msg": "Invalid request"}), 400

    if request.method == "POST":
        kpi = mongo.db.kpi.insert_one({
            "kpi_name": kpi_name,
            "kpi_json": kpi_json,
            "kra_json": kra_json
        })
        return jsonify(str(kpi.inserted_id)), 200
    elif request.method == "PUT":
        if id is None:
            return jsonify({"msg": "Invalid request"}), 400

        kpi = mongo.db.kpi.update({
            "_id": ObjectId(id)
        },
            {
            "$set": {
                "kpi_name": kpi_name,
                "kpi_json": kpi_json,
                "kra_json": kra_json
            }
        }, upsert=False)

        return jsonify(kpi), 200


@app.route("/assign_kpi/<string:user_id>/<string:kpi_id>", methods=["GET"])
@jwt_required
@admin_required
def assign_kpi_to_user(user_id, kpi_id):
    if kpi_id == -1:
        ret = mongo.db.users.update({
            "_id": ObjectId(user_id)
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
    return jsonify(ret), 200


@app.route("/assign_manager/<string:user_id>/<string:manager_id>/<int:weight>", methods=["GET"])
@jwt_required
@admin_required
def assign_manager(user_id, manager_id, weight):
    if weight > 0:
        ret = mongo.db.users.find_one({
            "_id": ObjectId(manager_id)
        })
        if "role" in ret and (ret["role"] == "manager" or ret["role"] == "admin"):
            ret = mongo.db.users.update({
                "_id": ObjectId(user_id)
            }, {
                "$push": {
                    "managers": {
                        "_id": manager_id,
                        "weight": weight
                    }
                }
            })
        else:
            return jsonify({"msg": "user should be a manger"}), 500
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
    return jsonify(ret), 200


def get_manager_profile(manager):

    ret = mongo.db.users.find_one({
        "_id": ObjectId(manager["_id"])
    })
    # del ret["_id"]
    if "managers" in ret:
        del ret["managers"]
    if "password" in ret:
        del ret["password"]
    if "username" in ret:
        del ret["username"]
    if "kpi_id" in ret:
        del ret["kpi_id"]
    ret['_id'] = str(ret['_id'])
    if "weight" in ret:
        ret["weight"] = manager["weight"]
    return ret


@app.route('/profile', methods=['PUT', 'GET'])
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


def serialize_doc(doc):
    doc["_id"] = str(doc["_id"])
    return doc


@app.route('/user/list', methods=['GET'])
@jwt_required
@admin_required
def user_list():
    users = mongo.db.users.find({})
    users = [serialize_doc(user) for user in users]
    return jsonify(users), 200


@app.route('/user/role/<string:user_id>/<string:role>', methods=['PUT'])
@jwt_required
@admin_required
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
        return jsonify({"msg": "invalid role"}), 500


@app.route('/checkin', methods=["POST"])
@jwt_required
def add_checkin():
    if not request.json:
        abort(500)

    report = request.json.get("report", None)
    task_completed = request.json.get("task_completed", False)
    task_not_completed_reason = request.json.get(
        "task_not_completed_reason", "")
    highlight = request.json.get("highlight", "")

    if task_completed == 1:
        task_completed = True
    else:
        task_completed = False

    current_user = get_current_user()

    ret = mongo.db.reports.insert_one({
        "report": report,
        "task_completed": task_completed,
        "task_not_completed_reason": task_not_completed_reason,
        "highlight": highlight,
        "user": str(current_user["_id"]),
        "created_at": datetime.datetime.now(),
        "type": "daily"
    }).inserted_id
    return jsonify(str(ret)), 200


@app.route('/reports', methods=["GET"])
@jwt_required
def checkin_reports():
    current_user = get_current_user()
    docs = mongo.db.reports.find({
        "user": str(current_user["_id"])
    })
    docs = [serialize_doc(doc) for doc in docs]
    return jsonify(docs), 200


@app.route('/week_reports', methods=["GET"])
@jwt_required
def get_week_reports():
    current_user = get_current_user()

    today = datetime.date.today()
    last_sunday = today - datetime.timedelta(days=(today.weekday() + 1))
    last_monday = today - datetime.timedelta(days=(today.weekday() + 8))

    docs = mongo.db.reports.find({
        "user": str(current_user["_id"]),
        "created_at": {
            "$gte": last_monday.isoformat(),
            "$lte": last_sunday.isoformat()
        }
    })
    docs = [serialize_doc(doc) for doc in docs]

    return jsonify(docs), 200


@app.route('/weekly', methods=["POST", "GET"])
@jwt_required
def add_weekly_checkin():
    current_user = get_current_user()
    if request.method == "GET":
        docs = mongo.db.reports.find({
            "type": "weekly",
            "user": str(current_user["_id"])
        }).sort("created_at", 1)
        docs = [serialize_doc(doc) for doc in docs]
        return jsonify(docs), 200
    if not request.json:
        abort(500)

    k_highlight = request.json.get("k_highlight", None)
    extra = request.json.get("extra", "")
    select_days = request.json.get("select_days", [])
    difficulty = request.json.get("difficulty", 0)

    if k_highlight is None:
        return jsonify({"msg": "Invalid request"}), 500

    ret = mongo.db.reports.insert_one({
        "k_highlight": k_highlight,
        "extra": extra,
        "select_days": select_days,
        "user": str(current_user["_id"]),
        "created_at": datetime.datetime.now(),
        "type": "weekly",
        "is_reviewed": False,
        "difficulty": difficulty
    }).inserted_id
    return jsonify(str(ret)), 200


def get_manager_juniors(id):

    users = mongo.db.users.find({
        "managers": {
            "$elemMatch": {"_id": str(id)}
        }
    })
    user_ids = []
    for user in users:
        user_ids.append(str(user['_id']))
    return user_ids


def load_checkin(id):
    ret = mongo.db.report.find_one({
        "_id": ObjectId(id)
    })
    return serialize_doc(ret)


def add_checkin_data(weekly_report):
    select_days = weekly_report["select_days"]
    select_days = [load_checkin(day) for day in select_days]
    weekly_report["select_days"] = select_days
    return weekly_report


@app.route("/manager_weekly_all", methods=["GET"])
@jwt_required
@manager_required
def get_manager_weekly_list_all():
    current_user = get_current_user()
    juniors = get_manager_juniors(current_user['_id'])
    docs = mongo.db.reports.find({
        "type": "weekly",
        "user": {
            "$in": juniors
        }
    }).sort("created_at", 1)
    docs = [add_checkin_data(serialize_doc(doc)) for doc in docs]
    return jsonify(docs), 200


@app.route("/manager_weekly", methods=["GET"])
@app.route("/manager_weekly/<string:weekly_id>", methods=["POST"])
@jwt_required
@manager_required
def get_manager_weekly_list(weekly_id=None):

    current_user = get_current_user()
    if request.method == "GET":
        juniors = get_manager_juniors(current_user['_id'])

        docs = mongo.db.reports.find({
            "type": "weekly",
            "is_reviewed": False,
            "user": {
                "$in": juniors
            }
        }).sort("created_at", 1)
        docs = [add_checkin_data(serialize_doc(doc)) for doc in docs]
        return jsonify(docs), 200
    else:
        if not request.json:
            abort(500)

        difficulty = request.json.get("difficulty", 0)
        rating = request.json.get("rating", 0)
        comment = request.json.get("comment", None)

        if comment is None or weekly_id is None:
            return jsonify({"msg", "invalid request"}), 500

        ret = mongo.db.reports.update({
            "_id": ObjectId(weekly_id)
        }, {
            "$set": {
                "review": {
                    "difficulty": difficulty,
                    "rating": rating,
                    "comment": comment
                },
                "is_reviewed": True
            }
        }, upsert=False)

        return jsonify(ret)


@app.route("/360_reviewers", methods=["GET"])
@jwt_required
def review_360():
    current_user = get_current_user()
    user = mongo.db.users.find_one({
        "_id": ObjectId(current_user["_id"])
    })
    if "managers" not in user:
        return []
    else:
        ret = [get_manager_profile(manager) for manager in user["managers"]]
        return jsonify(ret)


@app.route("/360_reviews", methods=["GET", "POST"])
@app.route("/360_reviews/<string:review_id>", methods=["PUT"])
@jwt_required
def reviews_360(review_id=None):
    current_user = get_current_user()

    if request.method == "GET":
        docs = mongo.db.reviews_360.find({
            "user": current_user["_id"]
        })
        docs = [serialize_doc(doc) for doc in docs]
        print(docs)
        return jsonify(docs)

    if not request.json:
        abort(500)

    manager = request.json.get("manager", None)
    rating = request.json.get("rating", None)
    comment = request.json.get("comment", "")
    anon = request.json.get("anon", True)

    if manager is None or rating is None:
        abort(500)

    if anon == 0:
        anon = False
    else:
        anon = True

    if rating is None:
        abort(500)

    if not anon:
        user = current_user["_id"]
    else:
        user = ""
    if review_id is None:
        ret = mongo.db.reviews_360.insert_one({
            "rating": rating,
            "comment": comment,
            "anon": anon,
            "user": user
        }).inserted_id
        ret = str(ret)
    else:
        ret = mongo.db.reviews_360.update({
            "_id": ObjectId(review_id)
        }, {
            "$set": {
                "rating": rating,
                "comment": comment,
                "anon": anon,
                "user": user
            }
        })

    return jsonify(ret)


if __name__ == '__main__':
    app.run(debug=True)
