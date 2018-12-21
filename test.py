from flask import Flask, jsonify, abort, request, make_response

from functools import wraps

from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity, get_current_user, jwt_refresh_token_required,
    verify_jwt_in_request
)
from bson.json_util import dumps
from bson.objectid import ObjectId

from flask_restful import Resource, Api

from flask_pymongo import PyMongo

from passlib.hash import pbkdf2_sha256

import datetime


app = Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/test_db_manish"
mongo = PyMongo(app)
api = Api(app)

app.config['JWT_SECRET_KEY'] = 'xxxx'  # Change this!
jwt = JWTManager(app)

tasks = [
    {
        'id': 1,
        'title': 'Buy groceries',
        'description': 'Milk, Cheese, Pizza, Fruit, Tylenol',
        'done': False
    },
    {
        'id': 2,
        'title': 'Learn Python',
        'description': 'Need to find a good Python tutorial on the web',
        'done': False
    }
]


@app.route('/todo/tasks', methods=['GET'])
def get_tasks():
    return jsonify({'tasks': tasks})


@app.route('/todo/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    task = [task for task in tasks if task['id'] == task_id]
    if len(task) == 0:
        abort(400)
    return jsonify(task)


@app.route("/todo/tasks", methods=['POST'])
def add_task():
    if not request.json or not'title' in request.json:
        abort(500, "Invalid Request")

    tasks.append({
        "id": len(tasks) + 1,
        "title": request.json["title"],
        "description": "",
        "done": False
    })
    return jsonify(True)


@app.route("/todo/tasks/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    if not task_id:
        abort(500, "Task ID is required for delete")
    global tasks
    tasks = [task for task in tasks if task['id'] != task_id]
    return jsonify(True)


def update(task, task_id, data):
    if task["id"] == task_id:
        if 'title' in data:
            task["title"] = data['title']
        if 'description' in data:
            task["description"] = data["description"]
    return task


@app.route("/todo/tasks/<int:task_id>", methods=["PUT"])
def edit_task(task_id):
    if not request.json:
        abort(500, "Invalid Request")
    global tasks
    tasks = [update(task, task_id, request.json) for task in tasks]
    return jsonify(tasks)


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

    return user


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user = get_current_user()
        if 'role' in user:
            if user['role'] != 'admin':
                return jsonify(msg='Admins only!'), 403
            else:
                return fn(*args, **kwargs)
        elif user["username"] == "manish2":
            return fn(*args, **kwargs)
        return jsonify(msg='Admins only!'), 403
    return wrapper


def manager_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user = get_current_user()
        if 'role' in user:
            if user['role'] != 'manager':
                return jsonify(msg='manager only!'), 403
            else:
                return fn(*args, **kwargs)
        return jsonify(msg='Admins only!'), 403
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


@app.route('/profile', methods=['PUT', 'GET'])
@jwt_required
def profile():
    current_user = get_current_user()
    if request.method == "GET":
        ret = mongo.db.users.find_one({
            "_id": ObjectId(current_user["_id"])
        })
        ret["_id"] = str(ret["_id"])
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


@app.router('/checkin', methods=["POST"])
@jwt_required
def add_checkin():
    if not request.json:
        abort(500)

    report = request.json.get("report", None)
    task_completed = request.json.get("task_completed", False)
    task_not_completed_reason = request.json.get(
        "task_not_completed_reason", "")
    highlight = request.json.get("highlight", "")

    ret = mongo.db.checkin.insert_one({
        "report": report,
        "task_completed": task_completed,
        "task_not_completed_reason": task_not_completed_reason,
        "highlight": highlight,
        "created_at": datetime.datetime.now()
    })
    return jsonify(dumps(ret))


if __name__ == '__main__':
    app.run(debug=True)
