from sqlalchemy import create_engine,text
import os
from dotenv import load_dotenv

env = os.getenv('FLASK_ENV', 'development')
dotenv_path = f'.env.{env}'
load_dotenv(dotenv_path)

#print(os.environ["DB_CONNECTION_STR"])

db_connection_string = os.environ["DB_CONNECTION_STR"]
db_connection_string = db_connection_string.strip('"').strip("'")

engine = create_engine(db_connection_string)

def load_students_from_db():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM students"))
        students = []
        for row in result.all():
            students.append(dict(row._mapping))
        return students
    
def load_student_from_db(id):
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM students WHERE id = :val"), {"val": id})
        row = result.fetchone()
        if row is None:
            return None
        else:
            return dict(row._mapping)
        
def add_student_to_db(data):
    with engine.connect() as conn:
    
        query =text("INSERT INTO students (name,surname,department,email,going_to) VALUES\
                    (:name, :surname, :department, :email, :going_to)")
        conn.execute(query,{
                     "name":data['name'],
                     "surname":data['surname'],
                     "email":data['email'],
                     "going_to":data['going_to'],
                     "department":data['department'],
                     })
        conn.commit()
        
