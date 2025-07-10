import os
from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from bson import ObjectId

# قراءة رابط المونجو من متغير البيئة MONGO_URI
mongo_uri = os.environ.get("MONGO_URI")
if not mongo_uri:
    raise Exception("MONGO_URI environment variable is not set!")

# إنشاء اتصال MongoDB باستخدام المتغير
client = MongoClient(mongo_uri)
db = client["university_system"]

users = db.users
exam_rooms_collection = db.exam_rooms
quiz_results_collection = db.quiz_results
complaints_collection = db.complaints
payments_collection = db.payments

# تحديث بيانات الطلاب (مثال)
db.users.update_many(
    {"role": "student", "payment_status": {"$exists": False}},
    {"$set": {"payment_status": "not paid"}}
)

subjects_collection = db['subjects']

subjects_collection.update_one(
    {'_id': ObjectId('6869505e72d18af4c3b95a66')}, 
    {'$set': {'doctor_id': ObjectId('6869561965e2d6f5133bba6f')}} 
)

users.delete_many({"email": "admin@example.com"})
