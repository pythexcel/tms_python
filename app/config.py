URL = 'http://176.9.137.77/hr/ReactReduxHR/backend/attendance/API_HR/api.php'
URL_details = 'http://176.9.137.77/hr/ReactReduxHR/backend/attendance/sal_info/api.php'
#secret_key = '3dd7fe8a6ea2ea9afb9a7366980253b7'
default=[{
            "monthly_remainder":"Please create your monthly report",
            "weekly_remainder1":"you need to create your weekly",
            "weekly_remainder2":"You are past due your date for weekly report, you need to do your weekly report before Thursday. Failing to do so will automatically set your weekly review to 0 which will effect your overall score.",
            "review_activity":"you have weekly report's pending to be reviewed",
            "monthly_manager_reminder":"you have monthly report's pending to be reviewed",
            "missed_checkin":"you have missed"
            }]




checkin_score_scheduler_seconds = 90

overall_score_scheduler_hour = 16
overall_score_scheduler_min = 30

reset_cron_scheduler_hour =18
reset_cron_scheduler_min = 10

missed_checkin_scheduler_hour =14
missed_checkin_scheduler_min =48

weekly_remainder_scheduler_hour=14
weekly_remainder_scheduler_min=54

review_activity_scheduler_hour =14
review_activity_scheduler_min =46

disable_user_scheduler_hour=20
disable_user_scheduler_min=30

monthly_score_scheduler_hour=13
monthly_score_scheduler_min=10

monthly_remainder_scheduler_hour=18
monthly_remainder_scheduler_min=5

monthly_manager_reminder_scheduler_hour=14
monthly_manager_reminder_scheduler_min=30
