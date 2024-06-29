from flask import Flask, render_template,jsonify, request
from database import load_students_from_db, load_student_from_db,add_student_to_db

app = Flask(__name__)

@app.route("/")
def hello_world():
    students = load_students_from_db()
    return render_template("home.html",students=students)

@app.route("/api/students")
def list_students():
    students = load_students_from_db()
    return jsonify(students)

@app.route("/student/<id>")
def show_student(id):
    student = load_student_from_db(id)

    if not student:
        return "Not Found",404
    
    return render_template("studentpage.html",student=student)

@app.route("/signup", methods=["GET", "POST"])
def sign_up_page():
    if request.method == "POST":
        data = request.form.to_dict()
        add_student_to_db(data)
        return render_template("signedup.html",signedin=data)
    return render_template("signup_form.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0",debug=True)