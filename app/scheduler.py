
from app.util import serialize_doc
from app import token
from app import mongo
from bson.objectid import ObjectId
import numpy as np



def overall_reviewes():
    users = mongo.db.reports.find_one({"cron_checkin": False}, {'user': 1,'_id':0})
    id = users['user']
    
    docs = mongo.db.reports.update_one({
       "cron_checkin": False
    }, {
       "$set": {
           "cron_checkin": True
           }}, upsert=False)
    
    docs = mongo.db.reports.find({"user":str(id)})
    user = mongo.db.users.find_one({"_id":ObjectId(id)})
    weights = user['managers']
    all_weight=[]
    for weg in weights:
       weight = weg['weight'] 
       all_weight.append(weight) 
    docs = [serialize_doc(doc) for doc in docs]
    all_sum=[]
    for detail in docs:   
       review=detail['review']
       rating=review['rating']
       all_sum.append(rating)
    weighted_avg = np.average(all_sum, weights=all_weight) 
    ret = mongo.db.users.update({
            "_id": ObjectId(id)
        }, {
            "$set": {
                "Overall_rating":weighted_avg 
            }
        })
  






