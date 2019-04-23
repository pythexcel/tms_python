from app import mongo
from app.util import serialize_doc
import datetime
from bson.objectid import ObjectId



#Function of recent_activity for checkin_missed and reviewed.
def recent_activity():
    #Here we find a common variable in report
        users = mongo.db.reports.find({"cron_recent_activity":False})
        users = [serialize_doc(doc) for doc in users]
        #find user id
        for detail in users:
            id=detail['user']
            #update cron  variable True    
            docs = mongo.db.reports.update({
            "user":str(id)
            }, {
            "$set": {
            "cron_recent_activity": True
            }}, upsert=False)
        
            today = datetime.date.today()
            last_sunday = today - datetime.timedelta(days=(today.weekday() + 1))
            last_monday = today - datetime.timedelta(days=(today.weekday() + 8))
        #here find last week reports by user_id where review exists 
            docs = mongo.db.reports.find({
                "user": str(id),
                "review": {'$exists': True},  
                "created_at": {
                "$gte": datetime.datetime(last_monday.year, last_monday.month, last_monday.day),
                "$lte": datetime.datetime(last_sunday.year, last_sunday.month, last_sunday.day)
            }
            })
            docs = [serialize_doc(doc) for doc in docs]
            for a in docs:
                review=a['review']
                manager_id=review['manager_id']
            #find employee manager_id
            managers = mongo.db.users.find({
                "_id": ObjectId(str(manager_id))},{"username":1})
            managers = [serialize_doc(doc) for doc in managers]
            
            for a in managers:
                manager_name=a["username"]
            #check if docs are empty or not
            if not docs:
                return("review not available")
            else:
                ret = mongo.db.recent_activity.update({
                    "user": str(id)},
                    {"$set":{
                    "recent_activity":{
                    "created_at": datetime.datetime.now(),
                    "Message":"Your weekly report has been reviewed by "" " +manager_name
                    }}},upsert=True)
            
            last_day = today - datetime.timedelta(1)
            next_day = today + datetime.timedelta(1)
            #find reports by user_id
            reports = mongo.db.reports.find({
            "user": str(id),
            "type": "daily",
            "created_at": {
                "$gte": datetime.datetime(last_day.year, last_day.month, last_day.day),
                "$lte": datetime.datetime(next_day.year, next_day.month, next_day.day)
            }
            })
            reports = [serialize_doc(report) for report in reports]
            #here if reports list are empty then push msg in DB  
            if not reports:
                ret = mongo.db.recent_activity.update({
                    "user": str(id),},
                    {"$push":{"missed_checkin":{
                        "checkin_message":"You have missed your daily checkin"
                    }}})    




def reviewed_activity():
    # First take date time where weekly report is to be dealt with
        today = datetime.date.today()
        last_sunday = today - datetime.timedelta(days=(today.weekday() + 1))
        last_monday = today - datetime.timedelta(days=(today.weekday() + 8))
        #find user by a common variable
        users = mongo.db.reports.find({"cron_recent_activity":False})
        users = [serialize_doc(doc) for doc in users]
        #find user id
        for detail in users:
            id=detail['user']
        #find in users for manager details 
        docs = mongo.db.users.find({
                    "_id": ObjectId(id)})            
        docs = [serialize_doc(doc) for doc in docs] 
        for data in docs:
            manage = data['managers']
            
        #find manager id
        for data in manage:
            ID_ = data['_id']
          # First find the users which have the manager id in it's document
        users = mongo.db.users.find({
                "managers": {
                    "$elemMatch": {"_id": str(ID_)}
                }
                })
        users = [serialize_doc(doc) for doc in users]
        # Make a list of User_id and then fetch all the users/juniors belong to that manager
        user_ids = []
        for user in users:
            user_ids.append(str(user['_id']))
        # Now find weekly reports of all those users_id in the above list whose report is not reviewd 
        for data in  user_ids:
            docs = mongo.db.reports.find({
                "user":str(data),
                "review": {'$exists': True},
                "created_at": {
                "$gte": datetime.datetime(last_monday.year, last_monday.month, last_monday.day),
                "$lte": datetime.datetime(last_sunday.year, last_sunday.month, last_sunday.day)
                    }  
            },{"user":1})
            docs = [serialize_doc(doc) for doc in docs]   
            # Append those user records whose not been reviewd in user_id list
            user_id = []
            for user in docs:
                user_id.append(ObjectId(user['user']))
                
            docs = mongo.db.users.find({
                 "_id": {"$in": user_id} 
                        },{"username":1})
            docs = [serialize_doc(doc) for doc in docs]       
            
            name_list = []
            for data in docs:
                name_list.append(data['username'])
                
            for junior_name in name_list:
                # Then if we find that data exist in user_id report than update the manager recent activity with a date and message
                if user_id is not None: 
                    ret = mongo.db.recent_activity.update({
                    "user": str(ID_),},
                    {"$set":{"recent_activity":{
                    "created_at": datetime.datetime.now(),
                    "Message":"Your have not reviewed your juniors" " "+  junior_name  +" " "weekly report"
                    }}},upsert=True)





