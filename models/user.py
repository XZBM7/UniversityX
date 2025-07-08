from config import db
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

users = db.users

def create_user(role, name, email, password, stage=None, university_id=None):
    if users.find_one({'email': email}):
        return None 
    hashed_password = generate_password_hash(password)
    user = {
        'role': role, 
        'name': name,
        'email': email,
        'password': hashed_password,
        'stage': stage,
        'university_id': university_id,
        'subjects': [],   
    }
    result = users.insert_one(user)
    return str(result.inserted_id)

def get_user_by_email(email):
    return users.find_one({'email': email})

def get_user_by_id(id):
    return users.find_one({'_id': ObjectId(id)})

def update_user(id, data):
    return users.update_one({'_id': ObjectId(id)}, {'$set': data})

def delete_user(id):
    return users.delete_one({'_id': ObjectId(id)})

def check_password(user, password):
    return check_password_hash(user['password'], password)
