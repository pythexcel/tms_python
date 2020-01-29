import os

from flask import Flask, make_response, jsonify

from flask_cors import CORS

from apscheduler.schedulers.background import BackgroundScheduler

from app import db

mongo = db.init_db()

from app import token

jwt = token.init_token()

from app.scheduler import checkin_score,review_activity, update_croncheckin,weekly_remainder,recent_activity,overall_reviewes,disable_user,monthly_score,monthly_remainder,monthly_manager_reminder,missed_review_activity,weekly_rating_left
from app.config import checkin_score_scheduler_seconds,overall_score_scheduler_hour,overall_score_scheduler_min,reset_cron_scheduler_hour,reset_cron_scheduler_min,missed_checkin_scheduler_hour,missed_checkin_scheduler_min,weekly_remainder_scheduler_hour,weekly_remainder_scheduler_min,review_activity_scheduler_hour,review_activity_scheduler_min,disable_user_scheduler_hour,disable_user_scheduler_min,monthly_manager_reminder_scheduler_hour,monthly_manager_reminder_scheduler_min,monthly_remainder_scheduler_hour,monthly_remainder_scheduler_min,monthly_score_scheduler_hour,monthly_score_scheduler_min,missed_review_activity_scheduler_hour,missed_review_activity_scheduler_min,weekly_rating_left_scheduler_hour,weekly_rating_left_scheduler_min

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
    from app.api import threesixty
    from app.api import report
    from app.api import settings
    from app.api import monthly

    app.register_blueprint(auth.bp)
    app.register_blueprint(kpi.bp)
    app.register_blueprint(user.bp)
    app.register_blueprint(threesixty.bp)
    app.register_blueprint(report.bp)
    app.register_blueprint(settings.bp)
    app.register_blueprint(monthly.bp)

    # Scheduler which will run at interval of 60 seconds for user checkin score
    checkin_score_scheduler = BackgroundScheduler()
    checkin_score_scheduler.add_job(checkin_score, trigger='interval', seconds=checkin_score_scheduler_seconds)
    checkin_score_scheduler.start()
    
    # Scheduler which will run at interval of 60 seconds for overall user rating
    
    overall_scheduler = BackgroundScheduler()
    overall_scheduler.add_job(overall_reviewes, trigger='cron', day_of_week='mon-sat', hour=overall_score_scheduler_hour, minute=overall_score_scheduler_min)
    overall_scheduler.start()
    
    # Scheduler which will run every monday to friday at 12:30am in midnight
    reset_scheduler = BackgroundScheduler()
    reset_scheduler.add_job(update_croncheckin, trigger='cron', day_of_week='mon-sat', hour=reset_cron_scheduler_hour, minute=reset_cron_scheduler_min)
    reset_scheduler.start()
    
    recent_activity_scheduler = BackgroundScheduler()
    recent_activity_scheduler.add_job(recent_activity, trigger='cron', day_of_week='mon-sat', hour=missed_checkin_scheduler_hour, minute=missed_checkin_scheduler_min)
    recent_activity_scheduler.start()
    
    weekly_remainder_scheduler = BackgroundScheduler()
    weekly_remainder_scheduler.add_job(weekly_remainder, trigger='cron', day_of_week='mon-sat', hour=weekly_remainder_scheduler_hour, minute=weekly_remainder_scheduler_min)
    weekly_remainder_scheduler.start()
    
    weekly_rating_left_scheduler = BackgroundScheduler()
    weekly_rating_left_scheduler.add_job(weekly_rating_left, trigger='cron', day_of_week='mon-sat', hour=weekly_rating_left_scheduler_hour, minute=weekly_rating_left_scheduler_min)
    weekly_rating_left_scheduler.add_job(weekly_rating_left, trigger='cron', day_of_week='mon-sat', hour=14, minute=30)
    weekly_rating_left_scheduler.add_job(weekly_rating_left, trigger='cron', day_of_week='mon-sat', hour=15, minute=00)
    weekly_rating_left_scheduler.add_job(weekly_rating_left, trigger='cron', day_of_week='mon-sat', hour=15, minute=30)
    weekly_rating_left_scheduler.start()

    review_activity_scheduler = BackgroundScheduler()
    review_activity_scheduler.add_job(review_activity, trigger='cron', day_of_week='fri-sat', hour=review_activity_scheduler_hour, minute=review_activity_scheduler_min)
    review_activity_scheduler.start()

    disable_user_scheduler = BackgroundScheduler()
    disable_user_scheduler.add_job(disable_user, trigger='cron', day_of_week='mon-sat', hour=disable_user_scheduler_hour, minute=disable_user_scheduler_min)
    disable_user_scheduler.start()
    
    #monthly_score_scheduler = BackgroundScheduler()
    #monthly_score_scheduler.add_job(monthly_score, trigger='cron', day_of_week='mon-sat', hour=monthly_score_scheduler_hour, minute=monthly_score_scheduler_min)
    #monthly_score_scheduler.start()
    
    #monthly_remainder_scheduler = BackgroundScheduler()
    #monthly_remainder_scheduler.add_job(monthly_remainder, trigger='cron', day_of_week='mon-sat', hour=monthly_remainder_scheduler_hour, minute=monthly_remainder_scheduler_min)
    #monthly_remainder_scheduler.start()
    
    #monthly_manager_reminder_scheduler = BackgroundScheduler()
    #monthly_manager_reminder_scheduler.add_job(monthly_manager_reminder, trigger='cron', day_of_week='mon-sat', hour=monthly_manager_reminder_scheduler_hour,minute=monthly_manager_reminder_scheduler_min)
    #monthly_manager_reminder_scheduler.start()

    missed_review_activity_scheduler = BackgroundScheduler()
    missed_review_activity_scheduler.add_job(missed_review_activity, trigger='cron', day_of_week='mon-sat', hour=missed_review_activity_scheduler_hour,minute=missed_review_activity_scheduler_min)
    missed_review_activity_scheduler.start()


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
        disable_user_scheduler.shutdown()
        #monthly_score_scheduler.shutdown()
        #monthly_remainder_scheduler.shutdown()
        #monthly_manager_reminder_scheduler.shutdown()
        missed_review_activity_scheduler.shutdown()
        weekly_rating_left_scheduler.shutdown()
    
