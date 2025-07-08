from config import db
from bson.objectid import ObjectId

schedules = db.schedules

def create_schedule(subject_id, day, time, room, term):
    schedule = {
        'subject_id': ObjectId(subject_id),
        'day': day,
        'time': time,
        'room': room,
        'term': term
    }
    result = schedules.insert_one(schedule)
    return str(result.inserted_id)

def get_schedule_by_subject(subject_id):
    return list(schedules.find({'subject_id': ObjectId(subject_id)}))

def get_all_schedules():
    return list(schedules.find())

def update_schedule(id, data):
    return schedules.update_one({'_id': ObjectId(id)}, {'$set': data})

def delete_schedule(id):
    return schedules.delete_one({'_id': ObjectId(id)})
