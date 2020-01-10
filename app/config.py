URL = 'http://dynamic.hr.excellencetechnologies.in/'
notification_system_url = 'http://127.0.0.1:5000/' #'http://127.0.0.1:8000/' #'http://5.9.144.22:8005/'

button={"actions": [
                {
                    "name": "rating",
                    "text": "3",
                    "type": "button",
                    "style": "danger",
                    "value": "rating"
                },
                {
                    "name": "rating",
                    "text": "5",
                    "type": "button",
                    "style": "danger",
                    "value": "rating"
                },
                {
                    "name": "rating",
                    "text": "7",
                    "type": "button",
                    "style": "danger",
                    "value": "rating"
                },
                {
                    "name": "rating",
                    "text": "9",
                    "type": "button",
                    "style": "danger",
                    "value": "rating"
                }
            ]
    }


checkin_score_scheduler_seconds = 900000

overall_score_scheduler_hour = 16
overall_score_scheduler_min = 30

reset_cron_scheduler_hour =18
reset_cron_scheduler_min = 10

missed_checkin_scheduler_hour =11
missed_checkin_scheduler_min =30

weekly_remainder_scheduler_hour=13
weekly_remainder_scheduler_min=2

review_activity_scheduler_hour =12
review_activity_scheduler_min =30

disable_user_scheduler_hour=20
disable_user_scheduler_min=30

monthly_score_scheduler_hour=13
monthly_score_scheduler_min=10

monthly_remainder_scheduler_hour=14
monthly_remainder_scheduler_min=10

monthly_manager_reminder_scheduler_hour=14
monthly_manager_reminder_scheduler_min=30

missed_review_activity_scheduler_hour=12
missed_review_activity_scheduler_min=56

