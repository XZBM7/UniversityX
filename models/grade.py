from config import db
from bson.objectid import ObjectId

grades = db.grades

def add_or_update_grade(student_id, subject_id, grade_value):
    filter_query = {
        'student_id': ObjectId(student_id),
        'subject_id': ObjectId(subject_id)
    }
    update_data = {'grade': grade_value}
    result = grades.update_one(filter_query, {'$set': update_data}, upsert=True)
    return result.upserted_id or None

def get_grades_by_student(student_id):
    return list(grades.find({'student_id': ObjectId(student_id)}))

def get_grade(student_id, subject_id):
    return grades.find_one({
        'student_id': ObjectId(student_id),
        'subject_id': ObjectId(subject_id)
    })

def delete_grade(student_id, subject_id):
    return grades.delete_one({
        'student_id': ObjectId(student_id),
        'subject_id': ObjectId(subject_id)
    })
