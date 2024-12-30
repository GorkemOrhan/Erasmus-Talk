from flask import Blueprint, request, jsonify, render_template, redirect, url_for, session
from src.core.database import get_db
from src.utils.decorators import admin_required
from . import services

bp = Blueprint('account', __name__)

@bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        data = request.form.to_dict()
        
        # Split data into user and student data
        user_data = {
            'name': data['name'],
            'surname': data['surname'],
            'email': data['email'],
            'password': data['password']
        }
        
        student_data = {
            'department': data['department'],
            'going_to': data['going_to']
        }
        
        db = next(get_db())
        account_service = services.AccountService(db)
        user = account_service.register_student(user_data, student_data)
        
        if user is None:
            return render_template("account/signup.html", 
                                error="This email is already registered.",
                                form_data=data)
        
        session['signedin'] = {
            'id': user.id,
            'email': user.email,
            'name': user.name
        }
        return redirect(url_for('account.registration_success'))
    
    return render_template("account/signup.html")

@bp.route("/registration-success")
def registration_success():
    signedin = session.get('signedin')
    if not signedin:
        return "Error: No user data available", 400
    return render_template("account/registration-success.html", signedin=signedin)

@bp.route("/activate/<token>")
def activate_account(token):
    db = next(get_db())
    account_service = services.AccountService(db)
    
    if account_service.activate_account(token):
        return redirect(url_for('account.login'))
    return "Invalid or expired activation token", 400

@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({"message": "Email and password are required"}), 400
        
        db = next(get_db())
        account_service = services.AccountService(db)
        user = account_service.verify_credentials(email, password)
        
        if user:
            session['signedin'] = user
            return jsonify({
                "user": user,
                "message": "Login successful"
            }), 200
        
        return jsonify({"message": "Invalid email or password"}), 401
    
    return render_template("account/login.html")

@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('main.index'))

@bp.route("/admin/students")
@admin_required
def admin_students():
    db = next(get_db())
    account_service = services.AccountService(db)
    students = account_service.get_all_students()
    return render_template("admin/students.html", students=students) 