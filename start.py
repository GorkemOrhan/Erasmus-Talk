import os

#os.environ['FLASK_ENV'] = 'test'
from flask_debugtoolbar import DebugToolbarExtension
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
import requests
from database import load_students_from_db, load_student_from_db, add_student_to_db, verify_user_credentials
import urllib.parse
import jwt
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.debug = True
app.secret_key = os.urandom(24)
toolbar = DebugToolbarExtension(app)
JWT_SECRET = os.urandom(24)  # In production, use a stable secret key

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

@app.route("/api/login", methods=["POST"])
def login_api():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400
    
    # Verify credentials from database
    user = verify_user_credentials(email, password)
    
    if user:
        # Generate JWT token
        token = jwt.encode({
            'user_id': user['id'],
            'email': user['email'],
            'name': user['name'],
            'exp': datetime.utcnow() + timedelta(days=1)
        }, JWT_SECRET, algorithm="HS256")
        
        return jsonify({
            "token": token,
            "user": {
                "id": user['id'],
                "email": user['email'],
                "name": user['name']
            }
        }), 200
    else:
        return jsonify({"message": "Invalid email or password"}), 401

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
    if request.method == "POST":
        data = request.form.to_dict()
        signedin = add_student_to_db(data)
        print("Signed-in Data:", signedin)  # Debugging line
        session['signedin'] = signedin  # Store data in session
        return redirect(url_for('signed_up_page'))
    return render_template("account/signup.html")

@app.route("/login")
def login():
    return render_template("account/login.html")
@app.route("/signedup")
def signed_up_page():
    signedin = session.get('signedin')
    print("Retrieved Signed-in Data:", signedin)  # Debugging line
    if not signedin:
        # Handle the case where signedin is not available
        return "Error: No user data available", 400
    return render_template("signedup.html", signedin=signedin)
    return render_template("signedup.html", signedin=signedin)

## LinkedIn Login Begin ##

CLIENT_ID = "7731dqhcky4vxl"
CLIENT_SECRET = "mgrwygPvYHARgVki"
REDIRECT_URI = "http://localhost:5000/callback"
ACCESS_TOKEN = "AQXITqv6bCR8dndWD8A3qcyL7_H5ENRHZ6aVz84C1ZqQGYnHtz6cw8vHWl4X56D59BB89BDqUTWprXJ3PULQ9rNqEE1QlY70n30H8dQ_aqbH7PTayhsd6G9PStDP4wQJAhoWugOjnF51bahRC5NQUuHeo0tk4EozSGPmjdyOjTGRSNGplcj-b_MPRUiqYE2aRSNZ93VmvquhxOrXFQlT0wPYnl0ZfRqQ8ZYYqtaQNeVw2TGGU7Jtv2GBkglU5kwXsBSNu7skGdnY1-0L5ZJR4_-jLEnGm4kKPTAcqFeJTXwikPvrleMKrG6HbW5nnY8q3anRe440OEP-N3OKJdrapsaObEI_iQ"

@app.route("/loginvialinkedin")
def login_via_linkedin():
    linkedin_auth_url = (
        "https://www.linkedin.com/oauth/v2/authorization?"
        "response_type=code&"
        f"client_id={CLIENT_ID}&"
        f"redirect_uri={urllib.parse.quote(REDIRECT_URI)}&"
        "scope=openid profile email"
    )
    
    return redirect(linkedin_auth_url)

@app.route("/callback")
def callback():
    
    error = request.args.get('error')
    error_description = request.args.get('error_description')

    if error:
        return "error description: "+error_description

    code = request.args.get('code')
    if not code:
        return "Error: Missing 'code' parameter in the request.", 400
    
    access_token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    token_data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }
    token_response = requests.post(access_token_url, data=token_data)
    
    if token_response.status_code != 200:
        print("Failed to get access token:", token_response.text)
        return f"Error: Failed to get access token, {token_response.text}", 500

    token_json = token_response.json()
    access_token = token_json.get('access_token')

    profile_url = "https://api.linkedin.com/v2/userinfo"
    profile_headers = {'Authorization': f'Bearer {access_token}'}
    profile_response = requests.get(profile_url, headers=profile_headers)
    
    if profile_response.status_code != 200:
        print("Failed to get profile data:", profile_response.text)
        return f"Error: Failed to get profile data, {profile_response.text}", 500

    profile_data = profile_response.json()
    

    email_url = "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))"
    email_response = requests.get(email_url, headers=profile_headers)
    
    if email_response.status_code != 200:
        print("Failed to get email data:", email_response.text)
        return f"Error: Failed to get email data, {email_response.text}", 500

    email_data = email_response.json()
    
    print("Profile Data:", profile_data)
    print("Email Data:", email_data)
    
    if 'elements' in email_data:
        email = email_data['elements'][0]['handle~']['emailAddress']
    else:
        print("Email data format is incorrect:", email_data)
        return "Error: 'elements' key not found in email data", 500

    session['profile'] = profile_data
    session['email'] = email

    return redirect(url_for('hello_world'))

## LinkedIn Login End ##

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    return render_template("account/forgot-password.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0",port=7080, debug=True)
