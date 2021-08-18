tms_system_url = 'http://tms.api.excellencetechnologies.in/' #server ip and port on which tms code running.

URL = 'https://apistaginghr.excellencetechnologies.in/'

notification_system_url = 'https://excellence_notifyapi.exweb.in/' #'http://127.0.0.1:8000/' 

accountname = "notify_tms"
weekly_page_link="http://tms.excellencetechnologies.in/#/app/week/WeeklyReport?update=true"


default_skip_settings = {
    "skip_review":True,
    "only_manager_skip":True
}


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

easy_actions ={"actions": [
                {
                    "name": "rating",
                    "text": "Bad",
                    "type": "button",
                    "style": "danger",
                    "value": "rating"
                },
                {
                    "name": "rating",
                    "text": "Neutral",
                    "type": "button",
                    "style": "danger",
                    "value": "rating"
                },
                {
                    "name": "rating",
                    "text": "Good",
                    "type": "button",
                    "style": "danger",
                    "value": "rating"
                }
            ]
    } 


weekly_notification ={"actions": [
                {
                    "name": "rating",
                    "text": "Submit an automatic weekly report",
                    "url":"http://tms.excellencetechnologies.in/#/app/automateWeekly",
                    "type": "button",
                    "style": "danger",
                    "value": "rating"
                }]
                    }




checkin_score_scheduler_seconds = 90

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

weekly_rating_left_scheduler_hour=14
weekly_rating_left_scheduler_min=00
