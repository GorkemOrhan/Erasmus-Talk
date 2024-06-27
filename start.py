from flask import Flask, render_template,jsonify

app = Flask(__name__)

STUDENTS = [
    {
        "id": 1,
        "name": "Görkem",
        "surname": "Orhan",
        "department":"Computer Engineering",
        "going_to":"Bologna Universitty"
    },
    {
        "id": 2,
        "name": "John",
        "surname": "Connor",
        "department":"Industrial Engineering",
        "going_to":"Frei Universitat"
    },
    {
        "id": 3,
        "name": "Marcus",
        "surname": "Pietro",
        "department":"Electrical-Electronics Engineer",
        "going_to":"Antalya Bilim University"
    }
]

@app.route("/")
def hello_world():
    return render_template("home.html",students=STUDENTS)

@app.route("/api/students")
def list_students():
    return jsonify(STUDENTS)

if __name__ == "__main__":
    app.run(host="0.0.0.0",debug=True)