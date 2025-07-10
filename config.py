import os
from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from bson import ObjectId

from pymongo import MongoClient

MONGO_URI = "mongodb+srv://katafafa9:MyPass1234@universityx.6slxjqo.mongodb.net/university_system?retryWrites=true&w=majority&appName=UniversityX"

client = MongoClient(MONGO_URI)
db = client['university_system']

users = db.users
exam_rooms_collection = db.exam_rooms
quiz_results_collection = db.quiz_results
complaints_collection = db.complaints
payments_collection = db.payments
subjects_collection = db['subjects']

def initialize_db():
    # تحديث حالة الدفع للطلاب الذين ليس لديهم هذا الحقل
    result = users.update_many(
        {"role": "student", "payment_status": {"$exists": False}},
        {"$set": {"payment_status": "not paid"}}
    )
    print(f"Updated payment_status for {result.modified_count} students.")

    # تحديث الدكتور في مادة محددة
    update_result = subjects_collection.update_one(
        {'_id': ObjectId('6869505e72d18af4c3b95a66')},
        {'$set': {'doctor_id': ObjectId('6869561965e2d6f5133bba6f')}}
    )
    if update_result.modified_count > 0:
        print("Doctor ID updated for the subject.")
    else:
        print("No subject updated.")

    # حذف المستخدمين الذين لديهم البريد admin@example.com
    delete_result = users.delete_many({"email": "admin@example.com"})
    print(f"Deleted {delete_result.deleted_count} user(s) with email admin@example.com.")

# استدعاء الدالة مرة واحدة عند بداية التشغيل
# initialize_db()
