from flask import Blueprint, render_template, request, redirect, url_for, session, flash, send_file
from bson.objectid import ObjectId
from config import db
import datetime
import io
import csv
from flask import Response
import csv
from io import StringIO
from config import quiz_results_collection
from werkzeug.security import generate_password_hash, check_password_hash
import os
from werkzeug.utils import secure_filename
doctor_bp = Blueprint('doctor', __name__)

users_collection = db.users
subjects_collection = db.subjects
schedules_collection = db.schedules
grades_collection = db.grades
quizzes_collection = db.quizzes
messages_collection = db.messages

def doctor_required(func):
    from functools import wraps
    @wraps(func)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or session['user']['role'] != 'doctor':
            flash('Unauthorized access', 'danger')
            return redirect(url_for('auth.login'))
        return func(*args, **kwargs)
    return decorated_function

@doctor_bp.route('/dashboard')
@doctor_required
def dashboard():
    doctor_id = ObjectId(session['user']['id'])
    doctor = users_collection.find_one({'_id': doctor_id})

    subjects = list(subjects_collection.find({'_id': {'$in': doctor.get('subjects', [])}}))

    quizzes = list(quizzes_collection.find({'creator_id': doctor_id}))

    for quiz in quizzes:
        if isinstance(quiz.get('start_time'), str):
            quiz['start_time'] = datetime.datetime.fromisoformat(quiz['start_time'])
        if isinstance(quiz.get('end_time'), str):
            quiz['end_time'] = datetime.datetime.fromisoformat(quiz['end_time'])

    return render_template('doctor/dashboard.html', subjects=subjects, quizzes=quizzes)


@doctor_bp.route('/schedule')
@doctor_required
def schedule():
    doctor_id = ObjectId(session['user']['id'])
    doctor = users_collection.find_one({'_id': doctor_id})
    doctor_subjects = doctor.get('subjects', [])
    schedules = list(schedules_collection.find({'subject_id': {'$in': doctor_subjects}}))

    for s in schedules:
        subject = subjects_collection.find_one({'_id': s['subject_id']})
        s['subject_name'] = subject['name'] if subject else "Unknown"

    return render_template('doctor/schedule.html', schedules=schedules)

@doctor_bp.route('/subject_students/<subject_id>')
@doctor_required
def subject_students(subject_id):
    subject = subjects_collection.find_one({'_id': ObjectId(subject_id)})
    students = list(users_collection.find(
        {
            'role': 'student',
            'subjects': ObjectId(subject_id)
        },
        {
            'name': 1,
            'email': 1,
            'university_id': 1 
        }
    ))
    return render_template('doctor/subject_students.html', 
                         students=students, 
                         subject=subject)

import io
import csv
import datetime
from flask import send_file, flash, redirect, url_for, render_template, request
from bson.objectid import ObjectId

@doctor_bp.route('/add_quiz/<subject_id>', methods=['GET', 'POST'])
@doctor_required
def add_quiz(subject_id):
    import pprint

    doctor_id = session['user']['id']
    print(f"DEBUG: Doctor ID from session: {doctor_id}")
    print(f"DEBUG: Subject ID from URL: {subject_id}")

    subject_basic = subjects_collection.find_one({'_id': ObjectId(subject_id)})
    print("DEBUG: Subject found without doctor filter:")
    pprint.pprint(subject_basic)

    subject = subjects_collection.find_one({
        '_id': ObjectId(subject_id),
        'doctor_id': ObjectId(doctor_id)
    })
    print("DEBUG: Subject found with doctor filter:")
    pprint.pprint(subject)

    if not subject:
        flash('Subject not found or you are not authorized', 'danger')
        return redirect(url_for('doctor.dashboard'))


    if request.method == 'POST':
        try:
            title = request.form['title']
            start_time = request.form['start_time']
            end_time = request.form['end_time']
            duration = int(request.form['duration'])

            start_dt = datetime.datetime.fromisoformat(start_time)
            end_dt = datetime.datetime.fromisoformat(end_time)
            
            if start_dt >= end_dt:
                flash('End time must be after start time', 'danger')
                return redirect(url_for('doctor.add_quiz', subject_id=subject_id))

            questions = []
            question_count = int(request.form.get('num_questions', 1))
            
            for i in range(1, question_count + 1):
                q_text = request.form.get(f'question_{i}_text')
                if not q_text or q_text.strip() == '':
                    continue
                    
                options = [
                    request.form.get(f'question_{i}_option_1', '').strip(),
                    request.form.get(f'question_{i}_option_2', '').strip(),
                    request.form.get(f'question_{i}_option_3', '').strip(),
                    request.form.get(f'question_{i}_option_4', '').strip()
                ]
                
                if any(not opt for opt in options):
                    flash(f'Question {i}: All options must be filled', 'danger')
                    return redirect(url_for('doctor.add_quiz', subject_id=subject_id))
                
                try:
                    correct_option = int(request.form.get(f'question_{i}_correct'))
                    if correct_option not in [1, 2, 3, 4]:
                        raise ValueError
                except (ValueError, TypeError):
                    flash(f'Question {i}: Please select a valid correct option (1-4)', 'danger')
                    return redirect(url_for('doctor.add_quiz', subject_id=subject_id))

                questions.append({
                    'text': q_text.strip(),
                    'options': options,
                    'correct_option': correct_option
                })

            if len(questions) == 0:
                flash('You must add at least one question', 'danger')
                return redirect(url_for('doctor.add_quiz', subject_id=subject_id))

            quiz_data = {
                'subject_id': ObjectId(subject_id),
                'subject_name': subject.get('name'),
                'title': title,
                'start_time': start_dt,
                'end_time': end_dt,
                'duration': duration,
                'published': False,
                'questions': questions,
                'created_at': datetime.datetime.utcnow(),
                'creator_id': ObjectId(session['user']['id'])
            }

            result = quizzes_collection.insert_one(quiz_data)
            flash('Quiz created successfully!', 'success')
            return redirect(url_for('doctor.quiz_results', quiz_id=str(result.inserted_id)))

        except Exception as e:
            flash(f'Error creating quiz: {str(e)}', 'danger')
            return redirect(url_for('doctor.add_quiz', subject_id=subject_id))

    return render_template('doctor/add_quiz.html', subject_id=subject_id, subject=subject)


@doctor_bp.route('/quiz_results/<quiz_id>')
@doctor_required
def quiz_results(quiz_id):
    quiz = quizzes_collection.find_one({'_id': ObjectId(quiz_id)})
    if not quiz:
        flash('Quiz not found.', 'danger')
        return redirect(url_for('doctor.dashboard'))

    results = list(db.quiz_results.find({'quiz_id': ObjectId(quiz_id)}))

    for res in results:
        student = users_collection.find_one({'_id': res['student_id']})
        res['student_name'] = student.get('name', 'Unknown') if student else 'Unknown'
        res['student_email'] = student.get('email', 'Unknown') if student else 'Unknown'

    return render_template('doctor/quiz_results.html', quiz=quiz, results=results)



from flask import Response
import csv
import io
from bson.objectid import ObjectId
from datetime import datetime

@doctor_bp.route('/export_quiz_results/<quiz_id>')
@doctor_required
def export_quiz_results(quiz_id):
    quiz = quizzes_collection.find_one({'_id': ObjectId(quiz_id)})
    if not quiz:
        flash('Quiz not found.', 'danger')
        return redirect(url_for('doctor.dashboard'))

    results = list(quiz_results_collection.find({'quiz_id': quiz['_id']}))

    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['Student Name', 'Student Email', 'Grade (Score / Total)', 'Submitted At'])

    for result in results:
        student = users_collection.find_one({'_id': result['student_id']})
        student_name = student.get('name', 'N/A')
        student_email = student.get('email', 'N/A')
        score = result.get('score', 0)
        total = result.get('total', 0)
        
        grade = f"{score} / {total}"
        
        submitted_at = result.get('submitted_at')
        submitted_at_str = submitted_at.strftime('%Y-%m-%d %H:%M') if submitted_at else 'N/A'

        writer.writerow([
        student_name,
        student_email,
        f'"{score} / {total}"', 
        submitted_at_str
])


    output.seek(0)

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={
            "Content-Disposition": f"attachment; filename=quiz_{quiz_id}_results.csv"
        }
    )

@doctor_bp.route('/delete_quiz/<quiz_id>', methods=['POST'])
@doctor_required
def delete_quiz(quiz_id):
    doctor_id = ObjectId(session['user']['id'])

    quiz = quizzes_collection.find_one({'_id': ObjectId(quiz_id), 'creator_id': doctor_id})
    if not quiz:
        flash('Quiz not found or not authorized', 'danger')
        return redirect(url_for('doctor.dashboard'))

    quiz_results_collection.delete_many({'quiz_id': quiz['_id']})

    quizzes_collection.delete_one({'_id': quiz['_id']})

    flash('Quiz deleted successfully.', 'success')
    return redirect(url_for('doctor.dashboard')) 


from datetime import datetime

@doctor_bp.route('/my_quizzes')
@doctor_required
def my_quizzes():
    quizzes = list(quizzes_collection.find({'creator_id': ObjectId(session['user']['id'])}))
    
    for q in quizzes:
        if isinstance(q.get('start_time'), str):
            q['start_time'] = datetime.fromisoformat(q['start_time'])
        if isinstance(q.get('end_time'), str):
            q['end_time'] = datetime.fromisoformat(q['end_time'])

    return render_template('doctor/my_quizzes.html', quizzes=quizzes, datetime=datetime)



@doctor_bp.route('/messages')
@doctor_required
def messages():
    doctor_id = ObjectId(session['user']['id'])
    msgs = messages_collection.find({'receiver_id': doctor_id})
    
    enriched_msgs = []
    for msg in msgs:
        student = users_collection.find_one({'_id': msg['sender_id']})
        enriched_msgs.append({
            '_id': msg['_id'],
            'sender_name': student.get('name', 'Unknown'),
            'sender_email': student.get('email'),
            'university_id': student.get('university_id'),
            'content': msg['message'],
            'timestamp': msg.get('timestamp'),
            'reply': msg.get('reply'),
            'reply_timestamp': msg.get('reply_timestamp'),
            'profile_image': student.get('profile_image')  
        })
    
    return render_template('doctor/messages.html', messages=enriched_msgs)



@doctor_bp.route('/reply_message/<message_id>', methods=['GET', 'POST'])
@doctor_required
def reply_message(message_id):
    message = messages_collection.find_one({'_id': ObjectId(message_id)})
    if not message:
        flash('Message not found', 'danger')
        return redirect(url_for('doctor.messages'))
    
    sender = users_collection.find_one({'_id': message['sender_id']})
    if not sender:
        flash('Sender not found', 'danger')
        return redirect(url_for('doctor.messages'))
    
    sender_image = sender.get('profile_image') or sender.get('profile_pic') or None
    
    context = {
        'message': {
            '_id': message_id,
            'content': message.get('message', ''),      
            'reply': message.get('reply', ''),
            'timestamp': message.get('timestamp'),
            'sender_name': sender.get('name', 'Unknown'),
            'sender_email': sender.get('email', ''),
            'university_id': sender.get('university_id', ''),
            'profile_image': sender_image           
        }
    }
    
    if request.method == 'POST':
        reply = request.form['reply']
        messages_collection.update_one(
            {'_id': ObjectId(message_id)},
            {'$set': {
                'reply': reply,
                'reply_timestamp': datetime.datetime.utcnow()
            }}
        )
        flash('Reply sent successfully', 'success')
        return redirect(url_for('doctor.messages'))
    
    return render_template('doctor/reply_message.html', **context)


from datetime import datetime 

from flask import request, redirect, url_for
from bson import ObjectId
import datetime

@doctor_bp.route('/edit_message/<message_id>', methods=['GET', 'POST'])
@doctor_required
def edit_message(message_id):
    message = messages_collection.find_one({'_id': ObjectId(message_id)})
    if not message:
        return "Message not found", 404

    if request.method == 'POST':
        new_reply = request.form.get('content')
        print(f"Received reply content: {new_reply!r}")

        if new_reply and new_reply.strip() != '':
            messages_collection.update_one(
                {'_id': ObjectId(message_id)},
                {'$set': {'reply': new_reply, 'reply_edited_at': datetime.datetime.utcnow()}}
            )
        return redirect(url_for('doctor.messages'))

    return render_template('doctor/edit_message.html', message=message)





@doctor_bp.route('/delete_message/<message_id>', methods=['POST', 'GET'])
@doctor_required
def delete_message(message_id):
    from bson.objectid import ObjectId

    messages_collection.delete_one({'_id': ObjectId(message_id)})
    flash('Message deleted successfully.', 'success')
    return redirect(url_for('doctor.messages'))

@doctor_bp.route('/logout')
def logout():
    session.pop('user', None)
    flash('Logged out.', 'success')
    return redirect(url_for('auth.login'))

@doctor_bp.route('/profile', methods=['GET', 'POST'])
@doctor_required
def profile():
    UPLOAD_FOLDER = 'static/uploads/profiles'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_name = request.form.get('name')
        new_password = request.form.get('new_password')
        changes_made = False

        user = users_collection.find_one({'_id': ObjectId(session['user']['id'])})
        if not user:
            flash('User not found', 'danger')
            return redirect(url_for('doctor.profile'))

        password_required = (new_name and new_name != session['user']['name']) or new_password
        if password_required:
            if not current_password:
                flash('Current password is required for changes', 'danger')
                return redirect(url_for('doctor.profile'))
            
            if not check_password_hash(user['password'], current_password):
                flash('Current password is incorrect', 'danger')
                return redirect(url_for('doctor.profile'))

        try:
            if new_name and new_name != session['user']['name']:
                users_collection.update_one(
                    {'_id': ObjectId(session['user']['id'])},
                    {'$set': {'name': new_name}}
                )
                session['user']['name'] = new_name
                changes_made = True

            if new_password:
                if len(new_password) < 8:
                    flash('Password must be at least 8 characters', 'danger')
                    return redirect(url_for('doctor.profile'))
                
                hashed_password = generate_password_hash(new_password)
                users_collection.update_one(
                    {'_id': ObjectId(session['user']['id'])},
                    {'$set': {'password': hashed_password}}
                )
                changes_made = True

            if 'profile_pic' in request.files:
                file = request.files['profile_pic']
                if file and file.filename != '':
                    if request.content_length > MAX_FILE_SIZE:
                        flash('File is too large (max 2MB)', 'danger')
                        return redirect(url_for('doctor.profile'))

                    if not ('.' in file.filename and 
                           file.filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS):
                        flash('Invalid file type. Allowed: png, jpg, jpeg, gif', 'danger')
                        return redirect(url_for('doctor.profile'))

                    ext = file.filename.rsplit('.', 1)[1].lower()
                    filename = f"{session['user']['id']}.{ext}"
                    filepath = os.path.join(UPLOAD_FOLDER, filename)

                    old_pic = user.get('profile_pic')
                    if old_pic and os.path.exists(os.path.join(UPLOAD_FOLDER, old_pic)):
                        try:
                            os.remove(os.path.join(UPLOAD_FOLDER, old_pic))
                        except OSError:
                            pass

                    file.save(filepath)
                    
                    users_collection.update_one(
                        {'_id': ObjectId(session['user']['id'])},
                        {'$set': {'profile_pic': filename}}
                    )
                    session['user']['profile_pic'] = filename
                    changes_made = True

            if changes_made:
                flash('Profile updated successfully', 'success')
            return redirect(url_for('doctor.profile'))

        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'danger')
            return redirect(url_for('doctor.profile'))

    user = users_collection.find_one({'_id': ObjectId(session['user']['id'])})
    return render_template('doctor/profile.html', user=user)



users_collection = db.users
subjects_collection = db.subjects
grades_collection = db.grades

@doctor_bp.route('/my_students_stats')
def my_students_stats():
    if 'user' not in session or session['user'].get('role') != 'doctor':
        return redirect(url_for('auth.login'))

    doctor_id = session['user'].get('_id') or session['user'].get('id')
    if not doctor_id:
        return redirect(url_for('auth.login'))

    doctor = users_collection.find_one({'_id': ObjectId(doctor_id)})
    if not doctor:
        return redirect(url_for('auth.login'))

    doctor_subjects = doctor.get('subjects', [])

    students = list(users_collection.find({
        'role': 'student',
        'subjects': {'$in': doctor_subjects}
    }))

    subjects_taught = list(subjects_collection.find({
        '_id': {'$in': doctor_subjects}
    }))

    student_stats = []

    for student in students:
        student_id = student['_id']

        grades = list(grades_collection.find({
            'student_id': student_id,
            'subject_id': {'$in': doctor_subjects}
        }))

        total = 0
        count = 0
        passed_subjects = 0

        for grade in grades:
            grade_value = grade.get('grade', 0)
            total += grade_value
            count += 1
            if grade_value >= 50:
                passed_subjects += 1

        avg_grade = total / count if count > 0 else 0
        pass_rate = (passed_subjects / count * 100) if count > 0 else 0

        student_data = {
            '_id': student_id,
            'name': student.get('name', 'Unknown'),
            'university_id': student.get('university_id', 'N/A'),
            'avg_grade': round(avg_grade, 2),
            'pass_rate': round(pass_rate, 1),
            'subject_count': count,
            'grades': [g.get('grade', 0) for g in grades]
        }

        student_stats.append(student_data)

    student_stats.sort(key=lambda x: x['avg_grade'], reverse=True)

    for rank, student in enumerate(student_stats, start=1):
        student['rank'] = rank

    total_students = len(student_stats)
    avg_grade_all = round(sum(s['avg_grade'] for s in student_stats) / total_students, 2) if total_students > 0 else 0
    avg_pass_rate = round(sum(s['pass_rate'] for s in student_stats) / total_students, 1) if total_students > 0 else 0

    overall_stats = {
        'total_students': total_students,
        'average_grade': avg_grade_all,
        'average_pass_rate': avg_pass_rate,
        'highest_grade': max((s['avg_grade'] for s in student_stats), default=0),
        'lowest_grade': min((s['avg_grade'] for s in student_stats), default=0),
    }

    return render_template(
        'doctor/students_statistics.html',
        students=student_stats,
        overall_stats=overall_stats,
        subjects_taught=subjects_taught,
        doctor=doctor
    )
