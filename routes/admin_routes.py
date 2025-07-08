from flask import Blueprint, render_template, request, redirect, url_for, session
from bson.objectid import ObjectId
from config import db
from werkzeug.security import generate_password_hash
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from config import db
import datetime
from config import quiz_results_collection
from config import complaints_collection , payments_collection



admin_bp = Blueprint('admin', __name__)

users_collection = db.users
subjects_collection = db.subjects
grades_collection = db.grades
schedules_collection = db.schedules
majors_collection = db.majors

def admin_required(func):
    from functools import wraps
    from flask import abort

    @wraps(func)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or session['user']['role'] != 'admin':
            ('غير مسموح بالدخول', 'danger')
            return redirect(url_for('auth.login'))
        return func(*args, **kwargs)
    return decorated_function

from flask import session

def get_current_user():
    if 'user_id' in session:
        return users_collection.find_one({'_id': session['user_id']})
    return None

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    total_students = users_collection.count_documents({'role': 'student'})
    total_doctors = users_collection.count_documents({'role': 'doctor'})
    total_subjects = subjects_collection.count_documents({})
    
    user = get_current_user() 
    
    return render_template('admin/dashboard.html', 
                         user=user,
                         total_students=total_students, 
                         total_doctors=total_doctors,
                         total_subjects=total_subjects)


@admin_bp.route('/add_student', methods=['GET', 'POST'])
@admin_required
def add_student():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        university_id = request.form['university_id']
        password = generate_password_hash(request.form['password'])
        stage = int(request.form['stage'])

        if users_collection.find_one({'email': email}):
            ('البريد الإلكتروني مسجل مسبقاً', 'danger')
            return redirect(url_for('admin.add_student'))

        user_data = {
            'role': 'student',
            'name': name,
            'email': email,
            'password': password,
            'university_id': university_id,
            'stage': stage,
            'subjects': []
        }
        users_collection.insert_one(user_data)
        ('تم إضافة الطالب بنجاح', 'success')
        return redirect(url_for('admin.list_students'))

    return render_template('admin/add_student.html')


@admin_bp.route('/students')
@admin_required
def list_students():
    students = list(users_collection.find({'role': 'student'}))
    return render_template('admin/list_students.html', students=students)


@admin_bp.route('/edit_student/<id>', methods=['GET', 'POST'])
@admin_required
def edit_student(id):
    student = users_collection.find_one({'_id': ObjectId(id), 'role': 'student'})
    if not student:
        ('الطالب غير موجود', 'danger')
        return redirect(url_for('admin.list_students'))

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        university_id = request.form['university_id']
        stage = int(request.form['stage'])

        users_collection.update_one({'_id': ObjectId(id)}, {'$set': {
            'name': name,
            'email': email,
            'university_id': university_id,
            'stage': stage
        }})
        ('تم تعديل بيانات الطالب', 'success')
        return redirect(url_for('admin.list_students'))

    return render_template('admin/edit_student.html', student=student)


@admin_bp.route('/delete_student/<id>')
@admin_required
def delete_student(id):
    users_collection.delete_one({'_id': ObjectId(id), 'role': 'student'})
    ('تم حذف الطالب', 'success')
    return redirect(url_for('admin.list_students'))


@admin_bp.route('/add_doctor', methods=['GET', 'POST'])
@admin_required
def add_doctor():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        stage = int(request.form['stage'])

        if users_collection.find_one({'email': email}):
            ('البريد الإلكتروني مسجل مسبقاً', 'danger')
            return redirect(url_for('admin.add_doctor'))

        user_data = {
            'role': 'doctor',
            'name': name,
            'email': email,
            'password': password,
            'stage': stage,
            'subjects': []
        }
        users_collection.insert_one(user_data)
        ('تم إضافة الدكتور بنجاح', 'success')
        return redirect(url_for('admin.list_doctors'))

    return render_template('admin/add_doctor.html')


@admin_bp.route('/doctors')
@admin_required
def list_doctors():
    doctors = list(users_collection.find({'role': 'doctor'}))

    for doctor in doctors:
        subject_names = []
        if 'subjects' in doctor:
            for subject_id in doctor['subjects']:
                subject = subjects_collection.find_one({'_id': subject_id})
                if subject:
                    subject_names.append(subject['name'])
        doctor['subject_names'] = subject_names

    return render_template('admin/list_doctors.html', doctors=doctors)




@admin_bp.route('/edit_doctor/<id>', methods=['GET', 'POST'])
@admin_required
def edit_doctor(id):
    doctor = users_collection.find_one({'_id': ObjectId(id), 'role': 'doctor'})
    if not doctor:
        ('الدكتور غير موجود', 'danger')
        return redirect(url_for('admin.list_doctors'))

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        stage = int(request.form['stage'])
        
        selected_subjects = request.form.getlist('subjects')
        subject_ids = [ObjectId(sub_id) for sub_id in selected_subjects]

        users_collection.update_one({'_id': ObjectId(id)}, {'$set': {
            'name': name,
            'email': email,
            'stage': stage,
            'subjects': subject_ids
        }})
        
        ('تم تعديل بيانات الدكتور', 'success')
        return redirect(url_for('admin.list_doctors'))

    all_subjects = list(subjects_collection.find())
    assigned_subject_ids = doctor.get('subjects', [])
    
    for subject in all_subjects:
        subject['is_assigned'] = subject['_id'] in assigned_subject_ids

    return render_template('admin/edit_doctor.html', 
                         doctor=doctor, 
                         subjects=all_subjects)

@admin_bp.route('/delete_doctor/<id>')
@admin_required
def delete_doctor(id):
    users_collection.delete_one({'_id': ObjectId(id), 'role': 'doctor'})
    ('تم حذف الدكتور', 'success')
    return redirect(url_for('admin.list_doctors'))


@admin_bp.route('/add_subject', methods=['GET', 'POST'])
@admin_required
def add_subject():
    if request.method == 'POST':
        name = request.form['name']
        hours = int(request.form['hours'])
        stage = int(request.form['stage'])
        term = request.form['term']

        subject_data = {
            'name': name,
            'hours': hours,
            'stage': stage,
            'term': term
        }
        subjects_collection.insert_one(subject_data)
        ('تم إضافة المادة بنجاح', 'success')
        return redirect(url_for('admin.list_subjects'))

    return render_template('admin/add_subject.html')


@admin_bp.route('/subjects')
@admin_required
def list_subjects():
    subjects = list(subjects_collection.find())
    global_registration_status = any(subject.get('registration_open', False) for subject in subjects)
    return render_template('admin/list_subjects.html', 
                         subjects=subjects,
                         global_registration_status=global_registration_status)

@admin_bp.route('/toggle-subject-registration', methods=['POST'])
@admin_required
def toggle_subject_registration():
    data = request.get_json()
    subject_id = data['subject_id']
    status = data['status']
    
    result = subjects_collection.update_one(
        {'_id': ObjectId(subject_id)},
        {'$set': {'registration_open': status}}
    )
    
    if result.modified_count > 0:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False}), 400

@admin_bp.route('/toggle-global-registration', methods=['POST'])
@admin_required
def toggle_global_registration():
    data = request.get_json()
    status = data['status']
    
    result = subjects_collection.update_many(
        {},
        {'$set': {'registration_open': status}}
    )
    
    if result.modified_count >= 0: 
        return jsonify({'success': True})
    else:
        return jsonify({'success': False}), 400

@admin_bp.route('/edit_subject/<id>', methods=['GET', 'POST'])
@admin_required
def edit_subject(id):
    subject = subjects_collection.find_one({'_id': ObjectId(id)})
    if not subject:
        ('المادة غير موجودة', 'danger')
        return redirect(url_for('admin.list_subjects'))

    if request.method == 'POST':
        name = request.form['name']
        hours = int(request.form['hours'])
        stage = int(request.form['stage'])
        term = request.form['term']

        subjects_collection.update_one({'_id': ObjectId(id)}, {'$set': {
            'name': name,
            'hours': hours,
            'stage': stage,
            'term': term
        }})
        ('تم تعديل المادة', 'success')
        return redirect(url_for('admin.list_subjects'))

    return render_template('admin/edit_subject.html', subject=subject)


@admin_bp.route('/delete_subject/<id>')
@admin_required
def delete_subject(id):
    subjects_collection.delete_one({'_id': ObjectId(id)})
    ('تم حذف المادة', 'success')
    return redirect(url_for('admin.list_subjects'))


@admin_bp.route('/assign_subject', methods=['GET', 'POST'])
@admin_required
def assign_subject_to_doctor():
    if request.method == 'POST':
        doctor_id = request.form['doctor_id']
        subject_id = request.form['subject_id']

        users_collection.update_one(
            {'_id': ObjectId(doctor_id)},
            {'$addToSet': {'subjects': ObjectId(subject_id)}}
        )

        subjects_collection.update_one(
            {'_id': ObjectId(subject_id)},
            {'$set': {'doctor_id': ObjectId(doctor_id)}}
        )

        flash('تم تعيين المادة للدكتور بنجاح', 'success')
        return redirect(url_for('admin.list_doctors'))

    doctors = list(users_collection.find({'role': 'doctor'}))
    subjects = list(subjects_collection.find())
    return render_template('admin/assign_subject.html', doctors=doctors, subjects=subjects)




@admin_bp.route('/add_grade', methods=['GET', 'POST'])
@admin_required
def add_grade():
    if request.method == 'POST':
        student_id = request.form['student_id']
        subject_id = request.form['subject_id']
        grade = float(request.form['grade'])

        student = users_collection.find_one({'_id': ObjectId(student_id)})
        if student and 'subjects' in student and ObjectId(subject_id) in student['subjects']:
            grades_collection.update_one(
                {'student_id': ObjectId(student_id), 'subject_id': ObjectId(subject_id)},
                {'$set': {'grade': grade, 'published': False}},
                upsert=True
            )
            ('تم حفظ الدرجة بنجاح', 'success')
        else:
            ('الطالب غير مسجل في هذه المادة', 'error')

    students = list(users_collection.find(
        {'role': 'student'},
        {'name': 1, 'subjects': 1, 'stage': 1}
    ))
    
    for student in students:
        student['subjects'] = [str(subj) for subj in student.get('subjects', [])]
    
    subjects = list(subjects_collection.find({}, {'name': 1, 'stage': 1}))

    return render_template('admin/add_grade.html', 
                        students=students, 
                        subjects=subjects)
    students = list(users_collection.find({'role': 'student'}))
    for student in students:
        student['subjects'] = [str(subj_id) for subj_id in student.get('subjects', [])]

    subjects = list(subjects_collection.find())
    return render_template('admin/add_grade.html', students=students, subjects=subjects)


@admin_bp.route('/list_grades')
@admin_required
def list_grades():
    grades = list(grades_collection.find())
    for grade in grades:
        student = users_collection.find_one({'_id': grade['student_id']})
        subject = subjects_collection.find_one({'_id': grade['subject_id']})
        grade['student_name'] = student['name'] if student else "غير معروف"
        grade['university_id'] = student.get('university_id', 'N/A') if student else "غير معروف"  
        grade['subject_name'] = subject['name'] if subject else "غير معروف"
    return render_template('admin/list_grades.html', grades=grades)


@admin_bp.route('/edit_grade/<id>', methods=['GET', 'POST'])
@admin_required
def edit_grade(id):
    grade = grades_collection.find_one({'_id': ObjectId(id)})
    if not grade:
        ('الدرجة غير موجودة', 'danger')
        return redirect(url_for('admin.list_grades'))

    if request.method == 'POST':
        grade_value = float(request.form['grade'])
        grades_collection.update_one({'_id': ObjectId(id)}, {'$set': {'grade': grade_value}})
        ('تم تعديل الدرجة', 'success')
        return redirect(url_for('admin.list_grades'))

    student = users_collection.find_one({'_id': grade['student_id']})
    subject = subjects_collection.find_one({'_id': grade['subject_id']})
    grade['student_name'] = student['name'] if student else "غير معروف"
    grade['subject_name'] = subject['name'] if subject else "غير معروف"
    return render_template('admin/edit_grade.html', grade=grade)


@admin_bp.route('/delete_grade/<id>')
@admin_required
def delete_grade(id):
    grades_collection.delete_one({'_id': ObjectId(id)})
    ('تم حذف الدرجة', 'success')
    return redirect(url_for('admin.list_grades'))


@admin_bp.route('/publish_grades', methods=['GET', 'POST'])
@admin_required
def publish_grades():
    if request.method == 'POST':
        subject_id = request.form['subject_id']
        grades_collection.update_many(
            {'subject_id': ObjectId(subject_id)},
            {'$set': {'published': True}}
        )
        ('تم نشر الدرجات لهذه المادة', 'success')
        return redirect(url_for('admin.publish_grades'))

    subjects = list(subjects_collection.find())
    return render_template('admin/publish_grades.html', subjects=subjects)


from flask import Blueprint, request, jsonify

@admin_bp.route('/get_grades_preview')
@admin_required
def get_grades_preview():
    subject_id = request.args.get('subject_id')
    if not subject_id:
        return jsonify({'error': 'Missing subject ID'})

    try:
        subject_oid = ObjectId(subject_id)
    except:
        return jsonify({'error': 'Invalid subject ID'})

    grades = list(grades_collection.find({'subject_id': subject_oid}))
    result = []

    total = 0
    count = 0

    for g in grades:
        student = users_collection.find_one({'_id': g['student_id']})
        if student:
            result.append({
                'ID': student.get('university_id', 'Unknown'),  
                'student_name': student.get('name', 'Unknown'),
                'grade': g.get('grade', 0),
                'published': g.get('published', False)
            })
            total += g.get('grade', 0)
            count += 1

    average = total / count if count > 0 else 0

    return jsonify({'grades': result, 'average': average})


@admin_bp.route('/add_schedule', methods=['GET', 'POST'])
@admin_required
def add_schedule():
    if request.method == 'POST':
        subject_id = request.form['subject_id']
        doctor_id = request.form['doctor_id']
        day = request.form['day']
        time = request.form['time']
        room = request.form['room']
        term = request.form['term']

        schedule_data = {
            'subject_id': ObjectId(subject_id),
            'doctor_id': ObjectId(doctor_id),
            'day': day,
            'time': time,
            'room': room,
            'term': term
        }

        schedules_collection.insert_one(schedule_data)
        ('تم إضافة الجدول بنجاح', 'success')
        return redirect(url_for('admin.list_schedules'))

    doctors = list(users_collection.find({'role': 'doctor'}))
    subjects = list(subjects_collection.find())
    return render_template('admin/add_schedule.html', doctors=doctors, subjects=subjects)



@admin_bp.route('/schedules')
@admin_required
def list_schedules():
    schedules = list(schedules_collection.find().sort('day', 1)) 

    for schedule in schedules:
        if 'subject_id' in schedule:
            subject = subjects_collection.find_one({'_id': schedule['subject_id']})
            if subject:
                schedule['subject_name'] = subject.get('name', 'Unknown Subject')
                schedule['subject_stage'] = subject.get('stage', 'Unknown Stage')
            else:
                schedule['subject_name'] = 'Unknown Subject'
                schedule['subject_stage'] = 'Unknown Stage'
        
        if 'doctor_id' in schedule:
            doctor = users_collection.find_one(
                {'_id': schedule['doctor_id'], 'role': 'doctor'},
                {'name': 1, 'email': 1}
            )
            if doctor:
                schedule['doctor_name'] = doctor.get('name', 'Unknown Doctor')
                schedule['doctor_email'] = doctor.get('email', '')
            else:
                schedule['doctor_name'] = 'Unknown Doctor'
                schedule['doctor_email'] = ''
        
        schedule.setdefault('day', 'Unknown Day')
        schedule.setdefault('time', 'Unknown Time')
        schedule.setdefault('room', 'Unknown Room')
        schedule.setdefault('term', 'Unknown Term')

    return render_template('admin/list_schedules.html', schedules=schedules)

exam_rooms_collection = db.exam_rooms 
subjects_collection = db.subjects
users_collection = db.users

def is_admin():
    return 'user' in session and session['user'].get('role') == 'admin'

@admin_bp.route('/exam_rooms')
def list_exam_rooms():
    if not is_admin():
        flash('غير مسموح بالدخول', 'danger')
        return redirect(url_for('auth.login'))

    try:
        exam_rooms = list(exam_rooms_collection.find().sort([('exam_date', 1), ('time', 1)]))
        for room in exam_rooms:
            subject = subjects_collection.find_one({'_id': room['subject_id']})
            room['subject_name'] = subject['name'] if subject else "غير معروف"
            room['formatted_date'] = room['exam_date'].strftime('%Y-%m-%d') if 'exam_date' in room else "غير محدد"
            room['formatted_day'] = room.get('day', 'غير محدد')
        return render_template('admin/list_exam_rooms.html', exam_rooms=exam_rooms)
    except Exception as e:
        flash(f'حدث خطأ أثناء جلب بيانات غرف الامتحانات: {str(e)}', 'danger')
        return redirect(url_for('admin.dashboard'))

from datetime import datetime

@admin_bp.route('/add_exam_room', methods=['GET', 'POST'])
def add_exam_room():
    if not is_admin():
        flash('غير مسموح بالدخول', 'danger')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        try:
            subject_id = request.form.get('subject_id')
            exam_date = request.form.get('exam_date')
            time = request.form.get('time')
            room = request.form.get('room')
            day = request.form.get('day')

            print("=== بيانات الإرسال ===")
            print("subject_id:", subject_id)
            print("exam_date:", exam_date)
            print("time:", time)
            print("room:", room)
            print("day:", day)

            if not all([subject_id, exam_date, time, room, day]):
                flash('يرجى ملء جميع الحقول المطلوبة', 'warning')
                print("⚠️ بعض الحقول ناقصة")
                return redirect(url_for('admin.add_exam_room'))

            try:
                exam_date_obj = datetime.strptime(exam_date, '%Y-%m-%d') 
            except ValueError:
                flash('صيغة التاريخ غير صحيحة. يرجى استخدام الصيغة YYYY-MM-DD', 'danger')
                print("❌ خطأ في تحويل التاريخ")
                return redirect(url_for('admin.add_exam_room'))

            print("✅ التاريخ بعد التحويل:", exam_date_obj)

            print("🔎 فحص التكرار...")
            existing_room = exam_rooms_collection.find_one({
                'room': room,
                'exam_date': exam_date_obj,
                'time': time
            })

            if existing_room:
                print("⚠️ الغرفة موجودة مسبقًا")
                flash('هذه الغرفة محجوزة بالفعل في هذا التوقيت', 'warning')
                return redirect(url_for('admin.add_exam_room'))

            exam_room_data = {
                'subject_id': ObjectId(subject_id),
                'exam_date': exam_date_obj,
                'day': day,
                'time': time,
                'room': room,
                'created_at': datetime.now()
            }

            result = exam_rooms_collection.insert_one(exam_room_data)
            print("✅ تم الإدخال بنجاح:", result.inserted_id)

            flash('تم إضافة غرفة الامتحان بنجاح', 'success')
            return redirect(url_for('admin.list_exam_rooms'))

        except Exception as e:
            print("❌ استثناء أثناء الإضافة:", str(e))
            flash(f'حدث خطأ أثناء إضافة غرفة الامتحان: {str(e)}', 'danger')
            return redirect(url_for('admin.add_exam_room'))

    try:
        subjects = list(subjects_collection.find())
        print("📚 عدد المواد:", len(subjects))
    except Exception as e:
        flash(f'حدث خطأ أثناء تحميل المواد: {str(e)}', 'danger')
        subjects = []

    return render_template('admin/add_exam_room.html', subjects=subjects)



@admin_bp.route('/edit_exam_room/<id>', methods=['GET', 'POST'])
def edit_exam_room(id):
    if not is_admin():
        flash('غير مسموح بالدخول', 'danger')
        return redirect(url_for('auth.login'))

    try:
        exam_room = exam_rooms_collection.find_one({'_id': ObjectId(id)})
        if not exam_room:
            flash('غرفة الامتحان غير موجودة', 'danger')
            return redirect(url_for('admin.list_exam_rooms'))

        if request.method == 'POST':
            subject_id = request.form.get('subject_id')
            exam_date = request.form.get('exam_date')
            time = request.form.get('time')
            room = request.form.get('room')
            day = request.form.get('day')


            if not all([subject_id, exam_date, time, room, day]):
                flash('يرجى ملء جميع الحقول المطلوبة', 'warning')
                return redirect(url_for('admin.edit_exam_room', id=id))

            try:
                exam_date_obj = datetime.strptime(exam_date, '%Y-%m-%d')  
            except ValueError:
                flash('صيغة التاريخ غير صحيحة', 'danger')
                return redirect(url_for('admin.edit_exam_room', id=id))

            existing_room = exam_rooms_collection.find_one({
                'room': room,
                'exam_date': exam_date_obj,
                'time': time,
                '_id': {'$ne': ObjectId(id)}
            })

            if existing_room:
                print("⚠️ الغرفة محجوزة بالفعل لغرفة أخرى")
                flash('هذه الغرفة محجوزة بالفعل في هذا التوقيت', 'warning')
                return redirect(url_for('admin.edit_exam_room', id=id))

            exam_rooms_collection.update_one(
                {'_id': ObjectId(id)},
                {'$set': {
                    'subject_id': ObjectId(subject_id),
                    'exam_date': exam_date_obj,
                    'day': day,
                    'time': time,
                    'room': room,
                    'updated_at': datetime.now()
                }}
            )

            print("✅ تم التعديل بنجاح")
            flash('تم تعديل غرفة الامتحان بنجاح', 'success')
            return redirect(url_for('admin.list_exam_rooms'))

        exam_room['formatted_date'] = exam_room['exam_date'].strftime('%Y-%m-%d') if 'exam_date' in exam_room else ""
        subjects = list(subjects_collection.find())
        return render_template('admin/edit_exam_room.html', exam_room=exam_room, subjects=subjects)

    except Exception as e:
        print("❌ استثناء أثناء التعديل:", str(e))
        flash(f'حدث خطأ أثناء تعديل غرفة الامتحان: {str(e)}', 'danger')
        return redirect(url_for('admin.list_exam_rooms'))


@admin_bp.route('/delete_exam_room/<id>')
def delete_exam_room(id):
    if not is_admin():
        flash('غير مسموح بالدخول', 'danger')
        return redirect(url_for('auth.login'))

    try:
        result = exam_rooms_collection.delete_one({'_id': ObjectId(id)})
        if result.deleted_count == 1:
            flash('تم حذف غرفة الامتحان بنجاح', 'success')
        else:
            flash('غرفة الامتحان غير موجودة', 'warning')
    except Exception as e:
        flash(f'حدث خطأ أثناء حذف غرفة الامتحان: {str(e)}', 'danger')
    
    return redirect(url_for('admin.list_exam_rooms'))


@admin_bp.route('/edit_schedule/<id>', methods=['GET', 'POST'])
@admin_required
def edit_schedule(id):
    schedule = schedules_collection.find_one({'_id': ObjectId(id)})
    if not schedule:
        ('الجدول غير موجود', 'danger')
        return redirect(url_for('admin.list_schedules'))

    if request.method == 'POST':
        subject_id = request.form['subject_id']
        doctor_id = request.form['doctor_id']
        day = request.form['day']
        time = request.form['time']
        room = request.form['room']
        term = request.form['term']

        schedules_collection.update_one({'_id': ObjectId(id)}, {'$set': {
            'subject_id': ObjectId(subject_id),
            'doctor_id': ObjectId(doctor_id),
            'day': day,
            'time': time,
            'room': room,
            'term': term
        }})
        ('تم تعديل الجدول', 'success')
        return redirect(url_for('admin.list_schedules'))

    subjects = list(subjects_collection.find())
    doctors = list(users_collection.find({'role': 'doctor'}))
    return render_template('admin/edit_schedule.html', schedule=schedule, subjects=subjects, doctors=doctors)


@admin_bp.route('/delete_schedule/<id>')
@admin_required
def delete_schedule(id):
    schedules_collection.delete_one({'_id': ObjectId(id)})
    ('تم حذف الجدول', 'success')
    return redirect(url_for('admin.list_schedules'))
@admin_bp.route('/profile', methods=['GET', 'POST'])
@admin_required
def admin_profile():
    if 'user' not in session or 'email' not in session['user']:
        ('Please login first', 'danger')
        return redirect(url_for('auth.login'))
    
    admin_email = session['user']['email']
    admin = users_collection.find_one({'email': admin_email, 'role': 'admin'})
    
    if not admin:
        ('Admin not found', 'danger')
        return redirect(url_for('admin.dashboard'))

    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        update_data = {
            'name': name,
            'email': email
        }

        if current_password and new_password and confirm_password:
            from werkzeug.security import check_password_hash
            if not check_password_hash(admin['password'], current_password):
                ('Current password is incorrect', 'danger')
                return redirect(url_for('admin.admin_profile'))
            
            if new_password != confirm_password:
                ('New passwords do not match', 'danger')
                return redirect(url_for('admin.admin_profile'))
                
            update_data['password'] = generate_password_hash(new_password)

        users_collection.update_one(
            {'_id': admin['_id']},
            {'$set': update_data}
        )
        session['user']['name'] = name
        session['user']['email'] = email
        session.modified = True

        ('Profile updated successfully', 'success')
        return redirect(url_for('admin.admin_profile'))

    return render_template('admin/profile.html', admin=admin)

@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    admin_id = session['user'].get('_id') or session['user'].get('id')
    admin = users_collection.find_one({'_id': ObjectId(admin_id)})
    
    if request.method == 'POST':
        if 'system_settings' in request.form:
            new_settings = {
                'site_name': request.form.get('site_name', 'University X'),
                'maintenance_mode': 'maintenance_mode' in request.form,
                'results_publishing': request.form.get('results_publishing', 'manual'),
                'default_theme': request.form.get('default_theme', 'light')
            }
            
            db.settings.update_one(
                {'name': 'system_settings'},
                {'$set': {'values': new_settings}},
                upsert=True
            )
            ('System settings updated successfully', 'success')
        
        elif 'email_settings' in request.form:
            email_settings = {
                'smtp_server': request.form.get('smtp_server'),
                'smtp_port': request.form.get('smtp_port'),
                'smtp_username': request.form.get('smtp_username'),
                'smtp_password': request.form.get('smtp_password'),
                'email_from': request.form.get('email_from')
            }
            
            from cryptography.fernet import Fernet
            key = Fernet.generate_key()
            cipher_suite = Fernet(key)
            
            encrypted_settings = {
                'smtp_server': email_settings['smtp_server'],
                'smtp_port': email_settings['smtp_port'],
                'smtp_username': cipher_suite.encrypt(email_settings['smtp_username'].encode()),
                'smtp_password': cipher_suite.encrypt(email_settings['smtp_password'].encode()),
                'email_from': email_settings['email_from'],
                'encryption_key': key
            }
            
            db.settings.update_one(
                {'name': 'email_settings'},
                {'$set': {'values': encrypted_settings}},
                upsert=True
            )
            ('Email settings updated successfully', 'success')
        
        return redirect(url_for('admin.admin_settings'))
    
    system_settings = db.settings.find_one({'name': 'system_settings'}) or {'values': {}}
    email_settings = db.settings.find_one({'name': 'email_settings'}) or {'values': {}}
    
    if email_settings.get('values', {}).get('encryption_key'):
        try:
            cipher_suite = Fernet(email_settings['values']['encryption_key'])
            email_settings['values']['smtp_username'] = cipher_suite.decrypt(
                email_settings['values']['smtp_username']
            ).decode()
            email_settings['values']['smtp_password'] = cipher_suite.decrypt(
                email_settings['values']['smtp_password']
            ).decode()
        except:
            pass
    
    return render_template('admin/settings.html',
                         admin=admin,
                         system_settings=system_settings.get('values', {}),
                         email_settings=email_settings.get('values', {}))

@admin_bp.route('/test_email', methods=['POST'])
@admin_required
def test_email():
    try:
        admin_email = session['user']['email']
        
        email_settings = {
            'smtp_server': request.form.get('smtp_server'),
            'smtp_port': request.form.get('smtp_port'),
            'smtp_username': request.form.get('smtp_username'),
            'smtp_password': request.form.get('smtp_password'),
            'email_from': request.form.get('email_from')
        }
        
        if not all(email_settings.values()):
            return jsonify({'success': False, 'message': 'All email settings are required'})
        
        import smtplib
        from email.mime.text import MIMEText
        
        msg = MIMEText('This is a test email from University X admin panel.')
        msg['Subject'] = 'University X - Test Email'
        msg['From'] = email_settings['email_from']
        msg['To'] = admin_email
        
        with smtplib.SMTP(email_settings['smtp_server'], int(email_settings['smtp_port'])) as server:
            server.starttls()
            server.login(email_settings['smtp_username'], email_settings['smtp_password'])
            server.send_message(msg)
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/complaints', methods=['GET', 'POST'])
@admin_required
def manage_complaints():
    complaints_enabled = db.settings.find_one({'name': 'complaints_settings'}) or {
        'values': {'enabled': True}
    }
    
    if request.method == 'POST' and 'toggle_complaints' in request.form:
        new_status = not complaints_enabled['values']['enabled']
        db.settings.update_one(
            {'name': 'complaints_settings'},
            {'$set': {'values.enabled': new_status}},
            upsert=True
        )
        flash(f'تم {"تفعيل" if new_status else "تعطيل"} نظام التظلمات', 'success')
        return redirect(url_for('admin.manage_complaints'))
    
    complaints = list(complaints_collection.find().sort('date', -1))
    
    for complaint in complaints:
        complaint['student'] = users_collection.find_one(
            {'_id': complaint['student_id']},
            {'name': 1, 'university_id': 1}
        )
        complaint['subject'] = subjects_collection.find_one(
            {'_id': complaint['subject_id']},
            {'name': 1}
        )
        if complaint['payment_id']:
            complaint['payment'] = payments_collection.find_one(
                {'_id': complaint['payment_id']}
            )
    
    return render_template('admin/manage_complaints.html',
                         complaints=complaints,
                         complaints_enabled=complaints_enabled['values']['enabled'])

@admin_bp.route('/review_complaint/<complaint_id>', methods=['GET', 'POST'])
@admin_required
def review_complaint(complaint_id):
    complaint = complaints_collection.find_one({'_id': ObjectId(complaint_id)})
    
    if not complaint:
        flash('الشكوى غير موجودة', 'danger')
        return redirect(url_for('admin.manage_complaints'))
    
    student = users_collection.find_one(
        {'_id': complaint['student_id']},
        {'name': 1, 'university_id': 1, 'email': 1}
    )
    subject = subjects_collection.find_one(
        {'_id': complaint['subject_id']},
        {'name': 1}
    )
    
    if request.method == 'POST':
        decision = request.form['decision']
        response = request.form.get('response', '')
        
        if decision == 'approve':
            new_status = 'approved'
            flash_msg = 'تم قبول التظلم'
        else:
            new_status = 'rejected'
            flash_msg = 'تم رفض التظلم'
        
        complaints_collection.update_one(
            {'_id': ObjectId(complaint_id)},
            {'$set': {
                'status': new_status,
                'admin_response': response,
                'reviewed_by': session['user']['id'],
                'review_date': datetime.datetime.now()
            }}
        )
        
        flash(flash_msg, 'success')
        return redirect(url_for('admin.manage_complaints'))
    
    return render_template('admin/review_complaint.html',
                         complaint=complaint,
                         student=student,
                         subject=subject)

#########################################

users_collection = db.users
tuition_fees_collection = db.tuition_fees  
payments_collection = db.payments           


@admin_bp.route('/manage_fees', methods=['GET', 'POST'])
@admin_required
def manage_fees():
    fees_settings = db.fees_settings.find_one({})
    if not fees_settings:
        fees_settings = {}

    if request.method == 'POST':
        if 'student_id' in request.form:  
            student_id = ObjectId(request.form['student_id'])
            stage = int(request.form['stage'])
            amount = float(request.form['amount'])
            
            payment_data = {
                'student_id': student_id,
                'amount': amount,
                'stage': stage,
                'payment_date': datetime.datetime.utcnow(),
                'method': 'admin',
                'status': 'completed',
                'transaction_id': f"ADM{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
                'admin_id': ObjectId(session['user']['id'])
            }
            db.payments.insert_one(payment_data)

            db.users.update_one(
                {'_id': student_id},
                {'$set': {
                    'paid_stage': stage,
                    'last_payment_date': datetime.datetime.utcnow()
                }}
            )

            flash(f'Payment of {amount} EGP for stage {stage} recorded successfully.', 'success')
            return redirect(url_for('admin.students_fees'))
        
        else:  
            stage_1_fee = float(request.form.get('stage_1_fee', 0))
            stage_2_fee = float(request.form.get('stage_2_fee', 0))
            stage_3_fee = float(request.form.get('stage_3_fee', 0))
            stage_4_fee = float(request.form.get('stage_4_fee', 0))

            new_settings = {
                'stage_1': stage_1_fee,
                'stage_2': stage_2_fee,
                'stage_3': stage_3_fee,
                'stage_4': stage_4_fee
            }

            if fees_settings:
                db.fees_settings.update_one({'_id': fees_settings['_id']}, {'$set': new_settings})
            else:
                db.fees_settings.insert_one(new_settings)

            flash('Fees updated successfully.', 'success')
            return redirect(url_for('admin.manage_fees'))

    return render_template('admin/manage_fees.html', fees=fees_settings)

@admin_bp.route('/students_fees')
@admin_required
def students_fees():
    users_collection = db.users
    students = list(users_collection.find({'role': 'student'}))
    
    fees_settings = db.fees_settings.find_one({}) or {}
    
    for student in students:
        stage = student.get("stage", 1)
        student['current_fee'] = fees_settings.get(f'stage_{stage}', 0)
        
        payment = db.payments.find_one(
            {'student_id': student['_id'], 'stage': stage, 'status': 'completed'},
            sort=[('payment_date', -1)]
        )
        student['payment_details'] = payment
        
        student['payment_status'] = 'paid' if payment else 'unpaid'

    return render_template('admin/students_fees.html', students=students, fees=fees_settings)


import traceback

@admin_bp.route('/record_payment/<student_id>', methods=['POST'])
@admin_required
def record_payment(student_id):
    try:
        student = db.users.find_one({'_id': ObjectId(student_id), 'role': 'student'})
        if not student:
            flash('Student not found.', 'danger')
            return redirect(url_for('admin.students_fees'))

        stage_str = request.form.get('stage', student.get('stage', 1))
        amount_str = request.form.get('amount', '0')

        try:
            stage = int(stage_str)
        except ValueError:
            flash('Invalid stage value.', 'danger')
            return redirect(url_for('admin.students_fees'))

        try:
            amount = float(amount_str)
        except ValueError:
            flash('Invalid amount value.', 'danger')
            return redirect(url_for('admin.students_fees'))

        payment_data = {
            'student_id': ObjectId(student_id),
            'amount': amount,
            'stage': stage,
            'payment_date': datetime.utcnow(),
            'method': 'admin',
            'status': 'completed',
            'transaction_id': f"ADM{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'admin_id': ObjectId(session['user']['id'])
        }
        db.payments.insert_one(payment_data)

        db.users.update_one(
            {'_id': ObjectId(student_id)},
            {'$set': {
                'paid_stage': stage,
                'last_payment_date': datetime.utcnow()
            }}
        )

        flash(f'Payment of {amount} EGP for stage {stage} recorded successfully.', 'success')
        return jsonify({'success': True, 'message': 'Payment recorded successfully'})

    except Exception as e:
        print(traceback.format_exc()) 
        flash(f'Error recording payment: {str(e)}', 'danger')
        return jsonify({'success': False, 'message': 'Error recording payment'})


@admin_bp.route('/delete_payment/<student_id>', methods=['POST'])
@admin_required
def delete_payment(student_id):
    try:
        student = db.users.find_one({'_id': ObjectId(student_id), 'role': 'student'})
        if not student:
            return jsonify({'success': False, 'message': 'Student not found'})

        delete_result = db.payments.delete_many({'student_id': ObjectId(student_id)})

        update_result = db.users.update_one(
            {'_id': ObjectId(student_id)},
            {'$unset': {'paid_stage': "", 'last_payment_date': ""}}
        )

        return jsonify({'success': True, 'message': 'Payment records deleted and student marked as unpaid.'})

    except Exception as e:
        print(f"Error deleting payment: {e}")
        return jsonify({'success': False, 'message': 'Server error while deleting payment'})


@admin_bp.route('/students_statistics')
@admin_required
def students_statistics():
    stages = {
        1: {'students': [], 'top3': [], 'stats': {}},
        2: {'students': [], 'top3': [], 'stats': {}},
        3: {'students': [], 'top3': [], 'stats': {}},
        4: {'students': [], 'top3': [], 'stats': {}}
    }
    
    students = list(users_collection.find({'role': 'student'}))
    
    all_students_ranking = [] 
    
    for student in students:
        stage = student.get('stage', 1)
        student_id = student['_id']
        
        grades = list(grades_collection.find({'student_id': student_id}))
        
        total = 0
        count = 0
        passed_subjects = 0
        for grade in grades:
            total += grade.get('grade', 0)
            count += 1
            if grade.get('grade', 0) >= 50:  
                passed_subjects += 1
        
        avg_grade = total / count if count > 0 else 0
        pass_rate = (passed_subjects / count * 100) if count > 0 else 0
        
        student_data = {
            '_id': student_id,
            'name': student.get('name', 'Unknown'),
            'university_id': student.get('university_id', 'N/A'),
            'stage': stage,
            'avg_grade': round(avg_grade, 2),
            'pass_rate': round(pass_rate, 1),
            'subject_count': count,
            'grades': [g.get('grade', 0) for g in grades]  
        }
        
        stages[stage]['students'].append(student_data)
        all_students_ranking.append(student_data)
    
    all_students_ranking.sort(key=lambda x: x['avg_grade'], reverse=True)
    
    for index, student in enumerate(all_students_ranking, start=1):
        student['rank'] = index
    
    for stage in stages:
        stages[stage]['students'].sort(key=lambda x: x['avg_grade'], reverse=True)
        
        stages[stage]['top3'] = stages[stage]['students'][:3]
        
        total_students = len(stages[stage]['students'])
        total_avg = sum(s['avg_grade'] for s in stages[stage]['students']) / total_students if total_students > 0 else 0
        total_pass_rate = sum(s['pass_rate'] for s in stages[stage]['students']) / total_students if total_students > 0 else 0
        
        stages[stage]['stats'] = {
            'total_students': total_students,
            'average_grade': round(total_avg, 2),
            'average_pass_rate': round(total_pass_rate, 1),
            'highest_grade': stages[stage]['top3'][0]['avg_grade'] if stages[stage]['top3'] else 0,
            'lowest_grade': stages[stage]['students'][-1]['avg_grade'] if stages[stage]['students'] else 0
        }
    
    overall_stats = {
        'total_students': len(all_students_ranking),
        'average_grade': round(sum(s['avg_grade'] for s in all_students_ranking) / len(all_students_ranking), 2) if all_students_ranking else 0,
        'average_pass_rate': round(sum(s['pass_rate'] for s in all_students_ranking) / len(all_students_ranking), 1) if all_students_ranking else 0,
        'highest_grade': max(s['avg_grade'] for s in all_students_ranking) if all_students_ranking else 0,
        'lowest_grade': min(s['avg_grade'] for s in all_students_ranking) if all_students_ranking else 0
    }
    
    return render_template('admin/students_statistics.html', 
                         stages=stages, 
                         overall_stats=overall_stats,
                         all_students_ranking=all_students_ranking)




@admin_bp.route('/add_admin', methods=['GET', 'POST'])
@admin_required
def add_admin():
    current_admin = users_collection.find_one({'_id': ObjectId(session['user']['id'])})

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        if users_collection.find_one({'email': email}):
            flash('البريد الإلكتروني مسجل مسبقاً', 'danger')
            return redirect(url_for('admin.add_admin'))

        admin_data = {
            'role': 'admin',
            'name': name,
            'email': email,
            'password': password,
            'created_at': datetime.datetime.now(),
            'created_by': current_admin['_id'] if current_admin else None
        }

        users_collection.insert_one(admin_data)
        flash('تم إضافة المسؤول بنجاح', 'success')
        return redirect(url_for('admin.list_admins'))

    return render_template('admin/add_admin.html')


@admin_bp.route('/admins')
@admin_required
def list_admins():
    current_admin = users_collection.find_one({'_id': ObjectId(session['user']['id'])})
    if not current_admin:
        flash('خطأ في بيانات الجلسة', 'danger')
        return redirect(url_for('auth.login'))

    admins = list(users_collection.find({'role': 'admin'}).sort('created_at', -1))

    creator_ids = [admin.get('created_by') for admin in admins if admin.get('created_by')]
    creators = {creator['_id']: creator['name'] for creator in users_collection.find(
        {'_id': {'$in': creator_ids}}
    )}

    for admin in admins:
        admin['creator_name'] = creators.get(admin.get('created_by'), 'System')

    return render_template('admin/list_admins.html', admins=admins, current_admin=current_admin)


@admin_bp.route('/edit_admin/<id>', methods=['GET', 'POST'])
@admin_required
def edit_admin(id):
    current_admin = users_collection.find_one({'_id': ObjectId(session['user']['id'])})

    admin = users_collection.find_one({'_id': ObjectId(id), 'role': 'admin'})
    if not admin:
        flash('المسؤول غير موجود', 'danger')
        return redirect(url_for('admin.list_admins'))

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']

        update_data = {
            'name': name,
            'email': email
        }

        if request.form.get('new_password'):
            update_data['password'] = generate_password_hash(request.form['new_password'])

        users_collection.update_one(
            {'_id': ObjectId(id)},
            {'$set': update_data}
        )

        flash('تم تحديث بيانات المسؤول بنجاح', 'success')
        return redirect(url_for('admin.list_admins'))

    return render_template('admin/edit_admin.html', admin=admin)


@admin_bp.route('/delete_admin/<id>')
@admin_required
def delete_admin(id):
    current_admin = users_collection.find_one({'_id': ObjectId(session['user']['id'])})

    if str(current_admin['_id']) == id:
        flash('لا يمكن حذف حسابك الخاص', 'danger')
        return redirect(url_for('admin.list_admins'))

    users_collection.delete_one({'_id': ObjectId(id), 'role': 'admin'})
    flash('تم حذف المسؤول بنجاح', 'success')
    return redirect(url_for('admin.list_admins'))

@admin_bp.route('/majors')
@admin_required
def list_majors():
    majors = list(majors_collection.find())
    return render_template('admin/list_majors.html', majors=majors)

@admin_bp.route('/majors/add', methods=['GET', 'POST'])
@admin_required
def add_major():
    if request.method == 'POST':
        name = request.form.get('name')
        if not name:
            flash('اسم التخصص مطلوب', 'danger')
            return redirect(url_for('admin.add_major'))

        majors_collection.insert_one({
            'name': name,
            'registration_open': False 
        })
        flash('تم إضافة التخصص بنجاح', 'success')
        return redirect(url_for('admin.list_majors'))

    return render_template('admin/add_major.html')

@admin_bp.route('/majors/toggle_registration/<major_id>', methods=['POST'])
@admin_required
def toggle_major_registration(major_id):
    major = majors_collection.find_one({'_id': ObjectId(major_id)})
    if not major:
        flash('التخصص غير موجود', 'danger')
        return redirect(url_for('admin.list_majors'))

    new_status = not major.get('registration_open', False)
    majors_collection.update_one(
        {'_id': ObjectId(major_id)},
        {'$set': {'registration_open': new_status}}
    )
    flash(f'تم {"فتح" if new_status else "إغلاق"} التسجيل للتخصص {major["name"]}', 'success')
    return redirect(url_for('admin.list_majors'))

@admin_bp.route('/majors/registrations')
@admin_required
def majors_registrations():
    majors = list(majors_collection.find())
    majors_with_students = []
    for major in majors:
        students = list(users_collection.find({'major_id': major['_id']}))
        majors_with_students.append({
            'major': major,
            'students': students
        })
    return render_template('admin/majors_registrations.html', majors_with_students=majors_with_students)

@admin_bp.route('/majors/delete/<major_id>', methods=['POST'])
@admin_required
def delete_major(major_id):
    major = majors_collection.find_one({'_id': ObjectId(major_id)})
    if not major:
        flash('Major not found.', 'danger')
        return redirect(url_for('admin.list_majors'))
    
    students_with_major = users_collection.count_documents({'major_id': ObjectId(major_id)})
    if students_with_major > 0:
        flash('Cannot delete major because students are registered in it.', 'warning')
        return redirect(url_for('admin.list_majors'))

    majors_collection.delete_one({'_id': ObjectId(major_id)})
    flash(f'Major "{major["name"]}" has been deleted.', 'success')
    return redirect(url_for('admin.list_majors'))
