from flask import Blueprint, request, render_template, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from config import db
from bson import ObjectId
import re

auth_bp = Blueprint('auth', __name__)

users_collection = db.users

def is_valid_email(input_str):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, input_str) is not None

@auth_bp.route('/')
def home():
    if 'user' in session:
        role = session['user']['role']
        if role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif role == 'doctor':
            return redirect(url_for('doctor.dashboard'))
        elif role == 'student':
            return redirect(url_for('student.dashboard'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']  
        password = request.form['password']

        try:
            if is_valid_email(username):
                user = users_collection.find_one({'email': username})
                error_msg = 'Incorrect email or password'
            else:
                user = users_collection.find_one({'university_id': username})
                error_msg = 'Incorrect university ID or password'

            if user and check_password_hash(user['password'], password):
                session['user'] = {
                    'id': str(user['_id']),
                    'role': user['role'],
                    'name': user['name'],
                    'email': user.get('email', ''),
                    'university_id': user.get('university_id', '')
                }
                flash('Logged in successfully', 'success')
                
                if user['role'] == 'admin':
                    return redirect(url_for('admin.dashboard'))
                elif user['role'] == 'doctor':
                    return redirect(url_for('doctor.dashboard'))
                elif user['role'] == 'student':
                    return redirect(url_for('student.dashboard'))
            else:
                flash(error_msg, 'danger')

        except Exception as e:
            print(f"Login error: {e}")
            flash('An error occurred during login', 'danger')

    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.pop('user', None)
    flash('Logged out successfully', 'success')
    return redirect(url_for('auth.login'))