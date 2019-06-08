import os

from flask import Flask, make_response, jsonify

from flask_cors import CORS

from apscheduler.schedulers.background import BackgroundScheduler

from app import db

mongo = db.init_db()

from app import token

jwt = token.init_token()

from app.scheduler import checkin_score,review_activity, update_croncheckin,weekly_remainder,recent_activity,overall_reviewes


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
    checkin_score_scheduler = BackgroundScheduler()
    checkin_score_scheduler.add_job(checkin_score, trigger='interval', seconds=80)
    checkin_score_scheduler.start()
    
    # Scheduler which will run at interval of 60 seconds for overall user rating
    
    overall_scheduler = BackgroundScheduler()
    overall_scheduler.add_job(overall_reviewes, trigger='cron', day_of_week='mon-sat', hour=15, minute=25)
    overall_scheduler.start()
    
    # Scheduler which will run every monday to friday at 12:30am in midnight
    reset_scheduler = BackgroundScheduler()
    reset_scheduler.add_job(update_croncheckin, trigger='cron', day_of_week='mon-sat', hour=18, minute=10)
    reset_scheduler.start()
    
    recent_activity_scheduler = BackgroundScheduler()
    recent_activity_scheduler.add_job(recent_activity, trigger='cron', day_of_week='mon-sat', hour=13, minute=50)
    recent_activity_scheduler.start()
    
    weekly_remainder_scheduler = BackgroundScheduler()
    weekly_remainder_scheduler.add_job(weekly_remainder, trigger='cron', day_of_week='mon-sat', hour=16, minute=45)
    weekly_remainder_scheduler.start()
    
    review_activity_scheduler = BackgroundScheduler()
    review_activity_scheduler.add_job(review_activity, trigger='cron', day_of_week='mon-sat', hour=11, minute=30)
    review_activity_scheduler.start()
     
    try:
        print("create app..")
        return app
    except:
        checkin_score_scheduler.shutdown()
        reset_scheduler.shutdown()
        overall_scheduler.shutdown()
        weekly_remainder_scheduler.shutdown()
        recent_activity_scheduler.shutdown()
        review_activity_scheduler.shutdown()
        
        
       
