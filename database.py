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
        
def check_email_exists(email):
    with engine.connect() as conn:
        query = text("SELECT COUNT(*) FROM students WHERE email = :email")
        result = conn.execute(query, {"email": email})
        count = result.scalar()
        return count > 0

def add_student_to_db(data):
    print(db_connection_string)

    with engine.connect() as conn:
        # Check if email already exists
        if check_email_exists(data['email']):
            return None  # Return None if email exists
            
        query = text("INSERT INTO students (name,surname,department,email,going_to,password) VALUES\
                    (:name, :surname, :department, :email, :going_to, :password)")
        conn.execute(query,{
                     "name": data['name'],
                     "surname": data['surname'],
                     "email": data['email'],
                     "going_to": data['going_to'],
                     "department": data['department'],
                     "password": data['password']
                     })
        conn.commit()
        return data
        
def verify_user_credentials(email, password):
    with engine.connect() as conn:
        # Get user with matching email
        query = text("SELECT * FROM students WHERE email = :email")
        result = conn.execute(query, {"email": email})
        user = result.fetchone()
        
        if user:
            # In production, use proper password hashing (e.g., bcrypt)
            # For now, simple password comparison
            if user.password == password:
                return {
                    'id': user.id,
                    'email': user.email,
                    'name': user.name,
                    'surname': user.surname
                }
        return None
        

        
