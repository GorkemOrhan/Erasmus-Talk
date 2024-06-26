from flask import Flask, render_template,jsonify

app = Flask(__name__)

STUDENTS = [
    {
        "id": 210201003,
        "name": "Görkem",
        "surname": "Orhan",
        "department":"Computer Engineering" 
    },
    {
        "id": 230204003,
        "name": "X",
        "surname": "Y",
        "department":"Industrial Engineering" 
    },
    {
        "id": 220202005,
        "name": "A",
        "surname": "B",
        "department":"Electrical-Electronics Engineer" 
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