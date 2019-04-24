import os

from flask import Flask, make_response, jsonify

from flask_cors import CORS

from apscheduler.schedulers.background import BackgroundScheduler

from app import db
mongo = db.init_db()


from app import token
jwt = token.init_token()

from app.scheduler import checkin_score, update_croncheckin, overall_reviewes,recent_activity,reviewed_activity

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping()

    CORS(app)

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    @app.errorhandler(400)
    def not_found(error):
        return make_response(jsonify(error='Not found'), 400)

    @app.errorhandler(500)
    def error_500(error):
        return make_response({}, 500)

    db.get_db(mongo=mongo, app=app)
    token.get_token(jwt=jwt, app=app)

    from app.api import auth
    from app.api import kpi
    from app.api import user
    from app.api import report
    from app.api import settings

    app.register_blueprint(auth.bp)
    app.register_blueprint(kpi.bp)
    app.register_blueprint(user.bp)
    app.register_blueprint(report.bp)
    app.register_blueprint(settings.bp)

    # Scheduler which will run at interval of 60 seconds for user checkin score
    scheduler = BackgroundScheduler()
    scheduler.add_job(checkin_score, trigger='interval', seconds=60)
    scheduler.start()
    
    # Scheduler which will run at interval of 60 seconds for overall user rating
    overall_scheduler = BackgroundScheduler()
    scheduler.add_job(overall_reviewes, trigger='interval', seconds=60)
    overall_scheduler.start()

    # Scheduler which will run every monday to friday at 12:30am in midnight
    reset_scheduler = BackgroundScheduler()
    reset_scheduler.add_job(update_croncheckin, trigger='cron', day_of_week='mon-fri', hour=12, minute=30)
    reset_scheduler.start()
    
    # This will trigger the scheduler for if user has not done his daily checkin and if weekly report is reviewed will trigger at mon-fri 11:00 am
    recent_activity_scheduler = BackgroundScheduler()
    scheduler.add_job(recent_activity, trigger='cron', day_of_week='mon-fri', hour=11, minute=05)
    scheduler.start()
    
    # This will trigger the scheduler for if manager has not reviewd his juniors weekly report at every monday 10:30 am
    reviewed_activity_scheduler = BackgroundScheduler()
    scheduler.add_job(reviewed_activity, trigger='cron', day_of_week='monday', hour=10, minute=30)
    scheduler.start()
    
    
    try:
        return app
    except:
        scheduler.shutdown()
        reset_scheduler.shutdown()
        overall_scheduler.shutdown()
        recent_activity_scheduler.shutdown()
        reviewed_activity_scheduler.shutdown()
