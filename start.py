from flask import Flask, render_template,jsonify
from database import load_students_from_db

app = Flask(__name__)

@app.route("/")
def hello_world():
    students = load_students_from_db()
    return render_template("home.html",students=students)

@app.route("/api/students")
def list_students():
    students = load_students_from_db()
    return jsonify(students)

if __name__ == "__main__":
    app.run(host="0.0.0.0",debug=True)