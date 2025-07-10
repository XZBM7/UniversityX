from flask import Blueprint, request, render_template, redirect, url_for, session, jsonify
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
    if request.method == 'GET':
        return render_template('auth/login.html')
    
    if request.method == 'POST':
        username = request.form.get('username')  
        password = request.form.get('password')

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
                
                if user['role'] == 'admin':
                    return jsonify({
                        'success': True,
                        'redirect': url_for('admin.dashboard'),
                        'message': 'Logged in successfully'
                    })
                elif user['role'] == 'doctor':
                    return jsonify({
                        'success': True,
                        'redirect': url_for('doctor.dashboard'),
                        'message': 'Logged in successfully'
                    })
                elif user['role'] == 'student':
                    return jsonify({
                        'success': True,
                        'redirect': url_for('student.dashboard'),
                        'message': 'Logged in successfully'
                    })
            else:
                return jsonify({
                    'success': False,
                    'message': error_msg
                }), 401

        except Exception as e:
            print(f"Login error: {e}")
            return jsonify({
                'success': False,
                'message': 'An error occurred during login'
            }), 500

@auth_bp.route('/logout')
def logout():
    session.pop('user', None)
    return jsonify({
        'success': True,
        'redirect': url_for('auth.login'),
        'message': 'Logged out successfully'
    })

@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'GET':
        return render_template('auth/forgot_password.html')
    
    if request.method == 'POST':
        university_id = request.form.get('university_id')
        email = request.form.get('email')

        user = users_collection.find_one({
            'university_id': university_id,
            'email': email
        })

        if user:
            session['reset_user'] = {
                'id': str(user['_id']),
                'role': user['role']
            }
            return jsonify({
                'success': True,
                'redirect': url_for('auth.reset_password'),
                'message': 'Identity verified. You can now reset your password.'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No matching user found with provided University ID and Email.'
            }), 404

@auth_bp.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    reset_user = session.get('reset_user')
    if not reset_user:
        return jsonify({
            'success': False,
            'redirect': url_for('auth.forgot_password'),
            'message': 'Session expired or invalid access.'
        }), 403
    
    if request.method == 'GET':
        return render_template('auth/reset_password.html')
    
    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if len(password) < 6:
            return jsonify({
                'success': False,
                'message': 'Password must be at least 6 characters long.'
            }), 400

        if password != confirm_password:
            return jsonify({
                'success': False,
                'message': 'Passwords do not match.'
            }), 400

        hashed_password = generate_password_hash(password)

        users_collection.update_one(
            {'_id': ObjectId(reset_user['id'])},
            {'$set': {'password': hashed_password}}
        )

        session.pop('reset_user', None)
        return jsonify({
            'success': True,
            'redirect': url_for('auth.login'),
            'message': 'Password updated successfully. You can now login.'
        })