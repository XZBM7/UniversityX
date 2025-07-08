from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from config import db
import datetime
from config import quiz_results_collection
from config import complaints_collection , payments_collection


student_bp = Blueprint('student', __name__)

users_collection = db.users
subjects_collection = db.subjects
grades_collection = db.grades
schedules_collection = db.schedules
exam_rooms_collection = db.exam_rooms  
quizzes_collection = db.quizzes
messages_collection = db.messages
majors_collection = db.majors


def student_required(func):
    from functools import wraps
    from flask import session, flash, redirect, url_for, request
    from bson import ObjectId

    @wraps(func)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or session['user'].get('role') != 'student':
            flash('غير مسموح بالدخول', 'danger')
            return redirect(url_for('auth.login'))
        
        student_id = ObjectId(session['user']['id'])
        student = db.users.find_one({'_id': student_id})

        if not student:
            flash('لم يتم العثور على بيانات الطالب', 'danger')
            return redirect(url_for('auth.login'))

        allowed_endpoints = [
            'student.pay_fees',
            'student.logout',
            'auth.logout',
            'static'
        ]

        paid_status = student.get('payment_status')
        paid_stage = student.get('paid_stage')
        current_stage = student.get('stage')

        if (paid_status != 'paid' or paid_stage != current_stage) and request.endpoint not in allowed_endpoints:
            flash('يجب سداد الرسوم الدراسية للمرحلة الحالية أولاً للوصول إلى المنصة', 'warning')
            return redirect(url_for('student.pay_fees'))

        return func(*args, **kwargs)
    
    return decorated_function


@student_bp.route('/dashboard')
@student_required
def dashboard():
    student_id = ObjectId(session['user']['id'])
    student = users_collection.find_one({'_id': student_id})

    subjects = list(subjects_collection.find({'_id': {'$in': student.get('subjects', [])}}))
    
    doctors = list(users_collection.find({
        'role': 'doctor',
        'subjects': {'$in': student.get('subjects', [])}
    }))
    
    quizzes = list(quizzes_collection.find({'subject_id': {'$in': student.get('subjects', [])}}))
    
    for doctor in doctors:
        doctor['_id'] = str(doctor['_id'])
    
    for quiz in quizzes:
        quiz['_id'] = str(quiz['_id'])
    
    for subject in subjects:
        subject['_id'] = str(subject['_id'])

    return render_template('student/dashboard.html', 
                         user=student, 
                         subjects=subjects, 
                         doctors=doctors, 
                         quizzes=quizzes)

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, session, current_app
)
@student_bp.route('/select_subjects', methods=['GET', 'POST'])
@student_required
def select_subjects():
    student_id = ObjectId(session['user']['id'])
    student = users_collection.find_one({'_id': student_id})
    if not student:
        flash('المستخدم غير موجود', 'danger')
        return redirect(url_for('auth.login'))

    stage = student.get('stage')
    if not stage:
        flash('لم يتم تعيين المرحلة للطالب', 'danger')
        return redirect(url_for('student.dashboard'))

    if request.method == 'POST':
        global_registration_closed = current_app.config.get('GLOBAL_REGISTRATION_CLOSED', False)
        if global_registration_closed:
            flash('التسجيل مغلق حالياً من قبل الإدارة', 'danger')
            return redirect(url_for('student.dashboard'))

        selected_ids = request.form.getlist('subjects')  

        if len(selected_ids) < 4 or len(selected_ids) > 6:
            flash('يجب اختيار من 4 إلى 6 مواد فقط', 'danger')
            return redirect(url_for('student.select_subjects'))

        count_open_subjects = subjects_collection.count_documents({
            '_id': {'$in': [ObjectId(sid) for sid in selected_ids]},
            'registration_open': True
        })
        if count_open_subjects != len(selected_ids):
            flash('بعض المواد المختارة غير متاحة للتسجيل حالياً', 'danger')
            return redirect(url_for('student.select_subjects'))

        users_collection.update_one(
            {'_id': student_id},
            {'$set': {'subjects': [ObjectId(sid) for sid in selected_ids]}}
        )
        flash('تم اختيار المواد بنجاح', 'success')
        return redirect(url_for('student.dashboard'))

    subjects = list(subjects_collection.find({'stage': stage}))

    return render_template(
        'student/select_subjects.html',
        subjects=subjects,
        user=student
    )

@student_bp.route('/view_schedule')
@student_required
def view_schedule():
    student_id = ObjectId(session['user']['id'])
    student = users_collection.find_one({'_id': student_id})

    selected_subject_ids = student.get('subjects', [])
    schedules = list(schedules_collection.find({'subject_id': {'$in': selected_subject_ids}}))

    for sch in schedules:
        subject = subjects_collection.find_one({'_id': sch['subject_id']})
        sch['subject_name'] = subject['name'] if subject else 'غير معروف'

        if 'doctor_id' in sch:
            doctor = users_collection.find_one({'_id': sch['doctor_id']})
            sch['doctor_name'] = doctor['name'] if doctor else 'غير معروف'
        else:
            sch['doctor_name'] = 'غير معروف'

    return render_template('student/view_schedule.html', schedules=schedules, user=student)


@student_bp.route('/exam_rooms')
@student_required
def exam_rooms():
    student_id = ObjectId(session['user']['id'])
    student = users_collection.find_one({'_id': student_id})

    selected_subject_ids = student.get('subjects', [])
    rooms = list(exam_rooms_collection.find({'subject_id': {'$in': selected_subject_ids}}))

    for room in rooms:
        subject = subjects_collection.find_one({'_id': room['subject_id']})
        room['subject_name'] = subject['name'] if subject else 'غير معروف'
        
        if 'exam_date' in room and isinstance(room['exam_date'], (datetime.datetime, datetime.date)):
            room['formatted_date'] = room['exam_date'].strftime('%Y-%m-%d')
        else:
            room['formatted_date'] = 'غير محدد'

        room['day'] = room.get('day', 'غير محدد')

    return render_template('student/exam_rooms.html', rooms=rooms, user=student)


@student_bp.route('/grades')
@student_required
def grades():
    student_id = ObjectId(session['user']['id'])
    student = users_collection.find_one({'_id': student_id})

    grades = list(grades_collection.find({
        'student_id': student_id,
        'published': True
    }))

    subjects_grades = []
    total_points = 0
    total_hours = 0

    def calculate_gpa_point(grade):
        if grade >= 90:
            return 4.0, "A+"
        elif grade >= 85:
            return 3.7, "A"
        elif grade >= 80:
            return 3.3, "B+"
        elif grade >= 75:
            return 3.0, "B"
        elif grade >= 70:
            return 2.7, "C+"
        elif grade >= 65:
            return 2.3, "C"
        elif grade >= 60:
            return 2.0, "D+"
        elif grade >= 50:
            return 2.0, "D"
        else:
            return 0.0, "F"

    for grade_entry in grades:
        subject = subjects_collection.find_one({'_id': grade_entry['subject_id']})
        if subject:
            hours = subject.get('hours', 0)
            grade_value = grade_entry.get('grade', 0)
            gpa_point, letter = calculate_gpa_point(grade_value)

            total_hours += hours
            total_points += gpa_point * hours

            subjects_grades.append({
                'subject_name': subject['name'],
                'grade': grade_value,
                'hours': hours,
                'letter': letter
            })

    gpa = (total_points / total_hours) if total_hours > 0 else 0

    return render_template('student/grades.html', subjects_grades=subjects_grades, gpa=gpa, user=student)



@student_bp.route('/chat/<doctor_id>', methods=['GET', 'POST'])
@student_required
def chat(doctor_id):
    student_id = ObjectId(session['user']['id'])
    doctor_oid = ObjectId(doctor_id)

    if request.method == 'POST':
        message_text = request.form['message']
        messages_collection.insert_one({
            'sender_id': student_id,
            'receiver_id': doctor_oid,
            'message': message_text,
            'timestamp': datetime.datetime.now()

        })
        return redirect(url_for('student.chat', doctor_id=doctor_id))

    messages = list(messages_collection.find({
        '$or': [
            {'sender_id': student_id, 'receiver_id': doctor_oid},
            {'sender_id': doctor_oid, 'receiver_id': student_id}
        ]
    }).sort('timestamp', 1))

    doctor = users_collection.find_one({'_id': doctor_oid})
    student = users_collection.find_one({'_id': student_id})

    return render_template('student/chat.html', messages=messages, doctor=doctor, user=student)

import datetime
from dateutil import parser

@student_bp.route('/quizzes')
@student_required
def quizzes():
    student_id = ObjectId(session['user']['id'])
    student = users_collection.find_one({'_id': student_id})

    selected_subject_ids = student.get('subjects', [])
    quizzes = list(quizzes_collection.find({'subject_id': {'$in': selected_subject_ids}}))

    now = datetime.datetime.utcnow()

    for quiz in quizzes:
        quiz['_id'] = str(quiz['_id'])

        start = quiz.get('start_time')
        end = quiz.get('end_time')

        if isinstance(start, str):
            start = parser.isoparse(start)
        if isinstance(end, str):
            end = parser.isoparse(end)

        if now < start:
            quiz['status'] = 'upcoming'
        elif now > end:
            quiz['status'] = 'ended'
        else:
            quiz['status'] = 'active'

        quiz['start_time_formatted'] = start.strftime('%Y-%m-%d %H:%M')
        quiz['end_time_formatted'] = end.strftime('%Y-%m-%d %H:%M')

    return render_template('student/quizzes.html', quizzes=quizzes, user=student)



from bson.objectid import ObjectId
import datetime
from dateutil import parser

@student_bp.route('/take_quiz/<quiz_id>', methods=['GET', 'POST'])
@student_required
def take_quiz(quiz_id):
    student_id = ObjectId(session['user']['id'])
    student = db.users.find_one({'_id': student_id})

    quiz = quizzes_collection.find_one({'_id': ObjectId(quiz_id)})
    if not quiz:
        flash('Quiz not found', 'danger')
        return redirect(url_for('student.quizzes'))

    existing_result = quiz_results_collection.find_one({
        'student_id': student_id,
        'quiz_id': quiz['_id']
    })
    if existing_result:
        flash('لقد أتممت هذا الاختبار بالفعل.', 'info')
        return redirect(url_for('student.quizzes'))

    def ensure_datetime(value):
        if isinstance(value, datetime.datetime):
            return value
        elif isinstance(value, str):
            return parser.isoparse(value)
        return None

    start = ensure_datetime(quiz.get('start_time'))
    end = ensure_datetime(quiz.get('end_time'))
    now = datetime.datetime.utcnow()



    if request.method == 'POST':
        score = 0
        questions = quiz.get('questions', [])
        total = len(questions)

        for i, question in enumerate(questions):
            correct_option_index = question.get('correct_option', 1) - 1
            options = question.get('options', [])
            correct_answer_text = options[correct_option_index] if 0 <= correct_option_index < len(options) else ''

            submitted_answer = request.form.get(f'answer_{i}', '').strip()

            if submitted_answer.lower() == correct_answer_text.strip().lower():
                score += 1

        quiz_results_collection.update_one(
            {'student_id': student_id, 'quiz_id': quiz['_id']},
            {
                '$set': {
                    'score': score,
                    'total': total,
                    'submitted_at': datetime.datetime.utcnow()
                }
            },
            upsert=True
        )

        return redirect(url_for('student.quizzes'))

    return render_template('student/take_quiz.html', quiz=quiz, user=student)



@student_bp.route('/edit_profile', methods=['GET', 'POST'])
@student_required
def edit_profile():
    student_id = ObjectId(session['user']['id'])
    student = users_collection.find_one({'_id': student_id})

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form.get('password', '')
        image_file = request.files.get('image')

        update_data = {'name': name, 'email': email}
        if password:
            update_data['password'] = generate_password_hash(password)
        if image_file and image_file.filename != '':
            import os
            filename = f"{student_id}_{image_file.filename}"
            upload_path = f"static/uploads/{filename}"
            image_file.save(upload_path)
            update_data['profile_image'] = filename

        users_collection.update_one({'_id': student_id}, {'$set': update_data})
        flash('تم تحديث بياناتك', 'success')
        return redirect(url_for('student.dashboard'))

    return render_template('student/edit_profile.html', user=student)




@student_bp.route('/complaints', methods=['GET', 'POST'])
@student_required
def complaints():
    complaints_settings = db.settings.find_one({'name': 'complaints_settings'})
    complaints_enabled = True
    if complaints_settings and 'values' in complaints_settings:
        complaints_enabled = complaints_settings['values'].get('enabled', True)

    if not complaints_enabled:
        flash('نظام التظلمات معطل حالياً، لا يمكنك إرسال تظلمات جديدة.', 'warning')
        return redirect(url_for('student.dashboard'))  

    student_id = ObjectId(session['user']['id'])
    student = users_collection.find_one({'_id': student_id})
    
    student_subjects = student.get('subjects', [])
    subjects = list(subjects_collection.find({'_id': {'$in': student_subjects}}))
    
    subject_map = {str(s['_id']): s for s in subjects}
    
    complaints = list(complaints_collection.find({'student_id': student_id}).sort('date', -1))

    total_complaints = len(complaints)
    pending_complaints = len([c for c in complaints if c['status'] in ['pending', 'pending_review']])
    resolved_complaints = len([c for c in complaints if c['status'] == 'resolved'])
    unpaid_complaints = len([c for c in complaints if c['payment_status'] == 'unpaid'])

    if request.method == 'POST':
        subject_id = ObjectId(request.form['subject_id'])
        complaint_text = request.form['complaint']

        if subject_id not in student_subjects:
            flash('هذه المادة غير مسجلة لديك', 'danger')
            return redirect(url_for('student.complaints'))

        complaint_data = {
            'student_id': student_id,
            'subject_id': subject_id,
            'complaint': complaint_text,
            'date': datetime.datetime.now(),
            'status': 'pending',
            'payment_status': 'unpaid',
            'admin_response': '',
            'payment_id': None
        }

        complaint_id = complaints_collection.insert_one(complaint_data).inserted_id

        flash('تم تقديم الشكوى، يرجى دفع الرسوم للمتابعة', 'success')
        return redirect(url_for('student.pay_complaint', complaint_id=complaint_id))

    return render_template('student/complaints.html',
                           subjects=subjects,
                           complaints=complaints,
                           subject_map=subject_map,
                           user=student,
                           total_complaints=total_complaints,
                           pending_complaints=pending_complaints,
                           resolved_complaints=resolved_complaints,
                           unpaid_complaints=unpaid_complaints)




@student_bp.route('/pay_complaint/<complaint_id>', methods=['GET', 'POST'])
@student_required
def pay_complaint(complaint_id):
    student_id = ObjectId(session['user']['id'])
    student = users_collection.find_one({'_id': student_id})
    
    complaint = complaints_collection.find_one({
        '_id': ObjectId(complaint_id),
        'student_id': student_id
    })
    
    if not complaint:
        flash('الشكوى غير موجودة', 'danger')
        return redirect(url_for('student.complaints'))
    
    if complaint['payment_status'] == 'paid':
        flash('تم دفع الرسوم مسبقاً', 'info')
        return redirect(url_for('student.complaints'))
    
    if request.method == 'POST':
        payment_data = {
            'complaint_id': ObjectId(complaint_id),
            'student_id': student_id,
            'amount': 50,
            'payment_date': datetime.datetime.now(),
            'method': 'simulated',
            'status': 'completed'
        }
        
        payment_id = payments_collection.insert_one(payment_data).inserted_id
        
        complaints_collection.update_one(
            {'_id': ObjectId(complaint_id)},
            {'$set': {
                'payment_status': 'paid',
                'status': 'pending_review',  
                'payment_id': payment_id
            }}
        )
        
        flash('تم دفع الرسوم بنجاح، جاري مراجعة شكواك', 'success')
        return redirect(url_for('student.complaints'))
    
    return render_template('student/pay_complaint.html', 
                         complaint=complaint, 
                         user=student)


@student_bp.route('/view_complaint/<complaint_id>')
@student_required
def view_complaint(complaint_id):
    student_id = ObjectId(session['user']['id'])
    student = users_collection.find_one({'_id': student_id})
    
    complaint = complaints_collection.find_one({
        '_id': ObjectId(complaint_id),
        'student_id': student_id
    })
    
    if not complaint:
        flash('الشكوى غير موجودة', 'danger')
        return redirect(url_for('student.complaints'))
    
    subject = subjects_collection.find_one({'_id': complaint['subject_id']})
    
    return render_template('student/view_complaint.html', 
                         complaint=complaint,
                         subject=subject,
                         user=student)

@student_bp.route('/delete_complaint/<complaint_id>', methods=['POST'])
@student_required
def delete_complaint(complaint_id):
    student_id = ObjectId(session['user']['id'])

    complaint = complaints_collection.find_one({
        '_id': ObjectId(complaint_id),
        'student_id': student_id
    })

    if not complaint:
        flash('Complaint not found or access denied.', 'danger')
        return redirect(url_for('student.complaints'))

    if complaint['payment_status'] == 'paid':
        flash('You cannot delete a complaint after payment.', 'warning')
        return redirect(url_for('student.complaints'))

    complaints_collection.delete_one({'_id': ObjectId(complaint_id)})

    flash('Complaint deleted successfully.', 'success')
    return redirect(url_for('student.complaints'))


###########################################################



@student_bp.route('/pay_fees', methods=['GET', 'POST'])
@student_required
def pay_fees():
    student_id = ObjectId(session['user']['id'])
    student = db.users.find_one({'_id': student_id})

    fees_settings = db.fees_settings.find_one({})
    stage = student.get('stage', 1)
    paid_stage = student.get('paid_stage', 0)
    amount = fees_settings.get(f'stage_{stage}', 0) if fees_settings else 0

    payment_status = 'paid' if paid_stage == stage else 'unpaid'

    if request.method == 'POST':
        if payment_status == 'paid':
            flash('You have already paid for the current academic year.', 'info')
            return redirect(url_for('student.pay_fees'))

        card_number = request.form.get('card_number')
        expiry = request.form.get('expiry_date')
        cvv = request.form.get('cvv')

        if not (card_number and expiry and cvv):
            flash('Please fill in all payment details.', 'danger')
            return redirect(url_for('student.pay_fees'))

        payment_data = {
       'student_id': ObjectId(student_id),
       'amount': amount,
       'stage': stage,
      'payment_date': datetime.utcnow(),  # ✅
      'method': 'admin',
      'status': 'completed',
      'transaction_id': f"ADM{datetime.now().strftime('%Y%m%d%H%M%S')}",  # ✅
      'admin_id': ObjectId(session['user']['id'])
}
        db.payments.insert_one(payment_data)

        db.users.update_one(
            {'_id': student_id},
            {'$set': {
                'payment_status': 'paid',
                'paid_stage': stage
            }}
        )

        session['user']['payment_status'] = 'paid'
        session['user']['paid_stage'] = stage
        session.modified = True

        flash('Payment completed successfully. Thank you!', 'success')
        return redirect(url_for('student.dashboard'))

    last_payment = db.payments.find_one({'student_id': student_id, 'stage': stage}, sort=[('payment_date', -1)])

    return render_template('student/pay_fees.html',
                           amount=amount,
                           stage=stage,
                           user=student,
                           paid_stage=paid_stage,
                           payment_status=payment_status,
                           current_year_month=datetime.datetime.now().strftime('%Y-%m'),
                           payment=last_payment)

from bson import ObjectId
import os
from flask import session, flash, redirect, url_for

@student_bp.route('/delete_profile_pic', methods=['POST'])
@student_required
def delete_profile_pic():
    user_id = ObjectId(session['user']['id'])
    user = users_collection.find_one({'_id': user_id})

    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('student.edit_profile'))

    profile_pic = user.get('profile_pic') or user.get('profile_image')
    if profile_pic:
        filepath = os.path.join('static', 'uploads', 'profiles', profile_pic)
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except Exception as e:
                flash(f"خطأ أثناء حذف الملف: {str(e)}", 'danger')

        users_collection.update_one(
            {'_id': user_id},
            {'$unset': {
                'profile_pic': "",
                'profile_image': ""
            }}
        )

        session['user'].pop('profile_pic', None)
        session['user'].pop('profile_image', None)

        flash('تم حذف الصورة بنجاح', 'success')
    else:
        flash('لا توجد صورة للحذف', 'info')

    return redirect(url_for('student.edit_profile'))



@student_bp.route('/select_major', methods=['GET', 'POST'])
@student_required
def select_major():
    student_id = ObjectId(session['user']['id'])
    student = users_collection.find_one({'_id': student_id})
    if not student:
        flash('User not found', 'danger')
        return redirect(url_for('auth.login'))

    # Only stage 3 students allowed
    if student.get('stage') != 3:
        flash('Major selection allowed only for stage 3 students', 'danger')
        return redirect(url_for('student.dashboard'))

    # Global registration closed flag (optional)
    global_registration_closed = current_app.config.get('MAJOR_REGISTRATION_CLOSED', False)
    if global_registration_closed:
        flash('Major registration is currently closed by administration', 'danger')
        return redirect(url_for('student.dashboard'))

    # Get majors with open registration
    open_majors = list(majors_collection.find({'registration_open': True}))

    if request.method == 'POST':
        selected_major_id = request.form.get('major')
        if not selected_major_id:
            flash('You must select exactly one major', 'danger')
            return redirect(url_for('student.select_major'))

        # Verify selected major is open
        major = majors_collection.find_one({'_id': ObjectId(selected_major_id), 'registration_open': True})
        if not major:
            flash('Selected major is not available for registration', 'danger')
            return redirect(url_for('student.select_major'))

        # Save selected major to user record
        users_collection.update_one(
            {'_id': student_id},
            {'$set': {'major_id': ObjectId(selected_major_id)}}
        )
        flash('Major selected successfully', 'success')
        return redirect(url_for('student.dashboard'))

    return render_template('student/select_major.html', majors=open_majors, user=student)

@student_bp.route('/logout')
def logout():
    session.pop('user', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('auth.login'))