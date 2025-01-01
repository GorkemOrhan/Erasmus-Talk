import os
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
import requests
from database import (
    load_students_from_db, 
    load_student_from_db, 
    add_student_to_db, 
    verify_user_credentials, 
    get_dashboard_stats,
    student_repository,
    engine
)
from email_service import queue_activation_email, start_scheduler, stop_scheduler, trigger_email_processing
import urllib.parse
import jwt
from datetime import datetime, timedelta
from functools import wraps
from dotenv import load_dotenv
import secrets
from sqlalchemy.sql import text
import atexit

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
JWT_SECRET = os.environ.get('JWT_SECRET', os.urandom(24))

# Only enable debug toolbar in development
if os.environ.get('FLASK_ENV') == 'development':
    app.debug = True

# Initialize scheduler flag
scheduler_started = False

@app.before_request
def initialize():
    """Initialize the application before first request."""
    global scheduler_started
    if not scheduler_started:
        start_scheduler()
        scheduler_started = True
        # Register cleanup on application exit
        atexit.register(stop_scheduler)

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        try:
            token = token.split(' ')[1]  # Remove 'Bearer ' prefix
            data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            current_user = data
        except:
            return jsonify({'message': 'Token is invalid'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or session['user'].get('role') != 'admin':
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/api/login", methods=["POST"])
def login_api():
    """Handle login API request."""
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    remember = data.get('remember', False)

    user = verify_user_credentials(email, password)
    if user:
        session['user'] = user
        if remember:
            session.permanent = True

        # Generate JWT token
        token = jwt.encode({
            'user_id': user['id'],
            'email': user['email'],
            'exp': datetime.utcnow() + timedelta(hours=24)
        }, JWT_SECRET)

        return jsonify({
            'token': token,
            'user': user,
            'redirect': '/admin/dashboard' if user.get('role') == 'admin' else '/'
        })
    else:
        return jsonify({'message': 'Invalid email or password'}), 401

@app.route("/")
def hello_world():
    students = load_students_from_db()
    return render_template("home.html", students=students)

@app.route("/api/students")
def list_students():
    students = load_students_from_db()
    return jsonify(students)

@app.route("/student/<id>")
def show_student(id):
    student = load_student_from_db(id)

    if not student:
        return "Not Found", 404
    
    return render_template("studentpage.html", student=student)

@app.route("/signup", methods=["GET", "POST"])
def sign_up_page():
    # Check if user is already logged in
    if 'user' in session:
        return redirect(url_for('admin_dashboard') if session['user'].get('role') == 'admin' else url_for('hello_world'))
    
    if request.method == "POST":
        data = request.form.to_dict()
        # Generate activation token
        data['activation_token'] = secrets.token_urlsafe(32)
        signedin = add_student_to_db(data)
        
        if signedin is None:
            # Email already exists, return form with data and error
            return render_template("account/signup.html", 
                                error="This email is already registered. Please use a different email or login to your existing account.",
                                form_data=data)
        
        session['signedin'] = signedin
        return redirect(url_for('registration_success'))
    return render_template("account/signup.html")

@app.route("/login")
def login():
    # Check if user is already logged in
    if 'user' in session:
        return redirect(url_for('admin_dashboard') if session['user'].get('role') == 'admin' else url_for('hello_world'))
    return render_template("account/login.html")

@app.route("/registration-success")
def registration_success():
    signedin = session.get('signedin')
    print("Retrieved Signed-in Data:", signedin)  # Debugging line
    if not signedin:
        # Handle the case where signedin is not available
        return "Error: No user data available", 400
    return render_template("account/registration-success.html", signedin=signedin)

@app.route("/activate/<token>")
def activate_account(token):
    """Activate a user account."""
    with engine.connect() as conn:
        # Begin transaction
        trans = conn.begin()
        try:
            # Find and activate user
            query = text("""
                UPDATE users
                SET is_active = true, activation_token = NULL
                WHERE activation_token = :token
                RETURNING id
            """)
            result = conn.execute(query, {"token": token})
            user_id = result.scalar()
            
            if not user_id:
                trans.rollback()
                return "Invalid or expired activation token", 400
            
            trans.commit()
            return redirect(url_for('login'))
        except:
            trans.rollback()
            raise

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    return render_template("account/forgot-password.html")

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    """Admin dashboard page."""
    stats = get_dashboard_stats()
    return render_template('admin/dashboard.html', stats=stats, user=session.get('user', {}))

@app.route("/admin/students")
@admin_required
def admin_students():
    """Admin students page."""
    return render_template("admin/students.html", user=session.get('user', {}))

@app.route("/admin/universities")
@admin_required
def admin_universities():
    # Add university management functionality
    return render_template("admin/universities.html")

@app.route("/admin/profile")
@admin_required
def admin_profile():
    # Add admin profile functionality
    return render_template("admin/profile.html")

@app.route("/admin/email-monitor")
@admin_required
def email_monitor():
    with engine.connect() as conn:
        # Get email statistics
        stats_query = text("""
            SELECT 
                COUNT(*) FILTER (WHERE status = 'pending') as pending_count,
                COUNT(*) FILTER (WHERE status = 'processing') as processing_count,
                COUNT(*) FILTER (WHERE status = 'sent') as sent_count,
                COUNT(*) FILTER (WHERE status = 'failed') as failed_count,
                COUNT(*) as total_count
            FROM pending_mails
        """)
        stats = dict(conn.execute(stats_query).fetchone()._mapping)
        
        # Get recent emails with logs
        recent_query = text("""
            SELECT 
                pm.id,
                pm.recipient_email,
                pm.recipient_name,
                pm.status,
                pm.retry_count,
                pm.created_at,
                pm.processed_at,
                mt.name as template_name,
                ml.error_message,
                ml.created_at as log_time
            FROM pending_mails pm
            JOIN mail_templates mt ON pm.template_id = mt.id
            LEFT JOIN (
                SELECT DISTINCT ON (pending_mail_id) *
                FROM mail_logs
                ORDER BY pending_mail_id, created_at DESC
            ) ml ON pm.id = ml.pending_mail_id
            ORDER BY pm.created_at DESC
            LIMIT 50
        """)
        recent_emails = [dict(row._mapping) for row in conn.execute(recent_query).fetchall()]
        
        return render_template(
            "admin/email-monitor.html",
            stats=stats,
            recent_emails=recent_emails
        )

@app.route("/admin/email-monitor/trigger", methods=["POST"])
@admin_required
def trigger_emails():
    """Manually trigger email processing."""
    success, message = trigger_email_processing()
    return jsonify({
        "success": success,
        "message": message
    }), 200 if success else 500

@app.route("/logout")
def logout():
    """Handle user logout."""
    # Clear session data
    session.clear()
    return redirect(url_for('hello_world'))

@app.route("/api/admin/students/<int:id>", methods=["DELETE"])
@admin_required
def delete_student(id):
    """Delete a student."""
    with engine.connect() as conn:
        # Begin transaction
        trans = conn.begin()
        try:
            # Delete student record
            query = text("""
                DELETE FROM students WHERE user_id = (
                    SELECT id FROM users WHERE id = :id
                )
            """)
            conn.execute(query, {"id": id})
            
            # Delete user record
            query = text("DELETE FROM users WHERE id = :id")
            conn.execute(query, {"id": id})
            
            trans.commit()
            return jsonify({"success": True})
        except:
            trans.rollback()
            return jsonify({"success": False, "message": "Failed to delete student"}), 500

@app.route("/api/admin/students")
@admin_required
def admin_students_api():
    """API endpoint for student list with pagination."""
    offset = request.args.get('offset', type=int, default=0)
    limit = request.args.get('limit', type=int, default=10)
    search = request.args.get('search', type=str)
    sort = request.args.get('sort', type=str)
    order = request.args.get('order', type=str)
    
    return jsonify(student_repository.get_paginated(
        offset=offset,
        limit=limit,
        search=search,
        sort=sort,
        order=order
    ))

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    app.run(host="0.0.0.0", port=port)
