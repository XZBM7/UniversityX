from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from bson import ObjectId

client = MongoClient("mongodb://localhost:27017/")
db = client["university_system"]
users = db.users
exam_rooms_collection = db.exam_rooms
quiz_results_collection = db.quiz_results
complaints_collection = db.complaints
payments_collection = db.payments

admin_user = {
    "name": "Admin - Omar",
    "email": "Omar@a.com",
    "password": generate_password_hash("Omar1234"),
    "role": "admin"
}

existing_admin = users.find_one({"email": admin_user["email"]})

if not existing_admin:
    users.insert_one(admin_user)
    print("✅ Admin user added")
else:
    print("⚠️ Admin user already exists, skipping insertion")

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

users.insert_one(admin_user)

# print("✅ Admin user added ")
