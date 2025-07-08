from config import db
from bson.objectid import ObjectId

subjects = db.subjects

def create_subject(name, hours, stage, term):
    subject = {
        'name': name,
        'hours': hours,
        'stage': stage,
        'term': term,
    }
    result = subjects.insert_one(subject)
    return str(result.inserted_id)

def get_subject_by_id(id):
    return subjects.find_one({'_id': ObjectId(id)})

def get_subjects_by_stage(stage):
    return list(subjects.find({'stage': stage}))

def update_subject(id, data):
    return subjects.update_one({'_id': ObjectId(id)}, {'$set': data})

def delete_subject(id):
    return subjects.delete_one({'_id': ObjectId(id)})
