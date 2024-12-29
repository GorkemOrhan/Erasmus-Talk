from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

env = os.getenv('FLASK_ENV', 'development')
dotenv_path = f'.env.{env}'
load_dotenv(dotenv_path)

db_connection_string = os.environ["DB_CONNECTION_STR"]
db_connection_string = db_connection_string.strip('"').strip("'")
engine = create_engine(db_connection_string)

def load_students_from_db():
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                u.*,
                s.department,
                s.going_to,
                array_agg(r.name) as roles 
            FROM users u
            JOIN students s ON u.id = s.user_id
            LEFT JOIN user_roles ur ON u.id = ur.user_id 
            LEFT JOIN roles r ON ur.role_id = r.id 
            GROUP BY u.id, s.department, s.going_to
        """))
        students = []
        for row in result.all():
            student = dict(row._mapping)
            student['roles'] = student['roles'][0] if student['roles'][0] else []
            students.append(student)
        return students
    
def load_student_from_db(id):
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 
                u.*,
                s.department,
                s.going_to,
                array_agg(r.name) as roles 
            FROM users u
            JOIN students s ON u.id = s.user_id
            LEFT JOIN user_roles ur ON u.id = ur.user_id 
            LEFT JOIN roles r ON ur.role_id = r.id 
            WHERE u.id = :val 
            GROUP BY u.id, s.department, s.going_to
        """), {"val": id})
        row = result.fetchone()
        if row is None:
            return None
        student = dict(row._mapping)
        student['roles'] = student['roles'][0] if student['roles'][0] else []
        return student
        
def check_email_exists(email):
    with engine.connect() as conn:
        query = text("SELECT COUNT(*) FROM users WHERE email = :email")
        result = conn.execute(query, {"email": email})
        count = result.scalar()
        return count > 0

def add_student_to_db(data):
    with engine.connect() as conn:
        # Check if email already exists
        if check_email_exists(data['email']):
            return None  # Return None if email exists
            
        # Begin transaction
        trans = conn.begin()
        try:
            # Insert base user first
            user_query = text("""
                INSERT INTO users (
                    name, surname, email, password, user_type
                )
                VALUES (
                    :name, :surname, :email, :password, 'student'
                )
                RETURNING id
            """)
            result = conn.execute(user_query, {
                "name": data['name'],
                "surname": data['surname'],
                "email": data['email'],
                "password": data['password']
            })
            user_id = result.scalar()

            # Insert student details
            student_query = text("""
                INSERT INTO students (user_id, department, going_to)
                VALUES (:user_id, :department, :going_to)
            """)
            conn.execute(student_query, {
                "user_id": user_id,
                "department": data['department'],
                "going_to": data['going_to']
            })

            # Assign student role
            role_query = text("""
                INSERT INTO user_roles (user_id, role_id)
                SELECT :user_id, id FROM roles WHERE name = 'student'
            """)
            conn.execute(role_query, {"user_id": user_id})

            trans.commit()
            return data
        except:
            trans.rollback()
            raise
        
def verify_user_credentials(email, password):
    with engine.connect() as conn:
        # Get user with roles and type-specific details
        query = text("""
            SELECT 
                u.*,
                s.department,
                s.going_to,
                a.admin_level,
                array_agg(r.name) as roles 
            FROM users u
            LEFT JOIN students s ON u.id = s.user_id
            LEFT JOIN admins a ON u.id = a.user_id
            LEFT JOIN user_roles ur ON u.id = ur.user_id 
            LEFT JOIN roles r ON ur.role_id = r.id 
            WHERE u.email = :email
            GROUP BY u.id, s.department, s.going_to, a.admin_level
        """)
        result = conn.execute(query, {"email": email})
        user = result.fetchone()
        
        if user:
            # In production, use proper password hashing (e.g., bcrypt)
            if user.password == password:
                user_data = {
                    'id': user.id,
                    'email': user.email,
                    'name': user.name,
                    'surname': user.surname,
                    'roles': user.roles[0] if user.roles[0] else [],
                    'user_type': user.user_type
                }
                
                # Add type-specific fields
                if user.user_type == 'student':
                    user_data.update({
                        'department': user.department,
                        'going_to': user.going_to
                    })
                elif user.user_type == 'admin':
                    user_data.update({
                        'admin_level': user.admin_level
                    })
                
                return user_data
        return None

def get_dashboard_stats():
    with engine.connect() as conn:
        # Get total students
        total_query = text("SELECT COUNT(*) FROM students")
        total_students = conn.execute(total_query).scalar()

        # Get active students
        active_query = text("""
            SELECT COUNT(*) FROM students s
            JOIN users u ON s.user_id = u.id
            WHERE u.is_active = true
        """)
        active_students = conn.execute(active_query).scalar()

        # Get monthly registrations
        month_ago = datetime.now() - timedelta(days=30)
        monthly_query = text("""
            SELECT COUNT(*) FROM students s
            JOIN users u ON s.user_id = u.id
            WHERE u.created_at >= :month_ago
        """)
        monthly_registrations = conn.execute(monthly_query, {"month_ago": month_ago}).scalar()

        # Get recent students
        recent_query = text("""
            SELECT 
                u.*,
                s.department,
                s.going_to,
                array_agg(r.name) as roles 
            FROM users u
            JOIN students s ON u.id = s.user_id
            LEFT JOIN user_roles ur ON u.id = ur.user_id 
            LEFT JOIN roles r ON ur.role_id = r.id 
            GROUP BY u.id, s.department, s.going_to
            ORDER BY u.created_at DESC 
            LIMIT 10
        """)
        recent_students = [dict(row._mapping) for row in conn.execute(recent_query).fetchall()]

        # Get popular universities
        university_query = text("""
            SELECT going_to, COUNT(*) as count 
            FROM students 
            GROUP BY going_to 
            ORDER BY count DESC 
            LIMIT 5
        """)
        university_stats = conn.execute(university_query).fetchall()
        university_labels = [row[0] for row in university_stats]
        university_data = [row[1] for row in university_stats]

        return {
            'total_students': total_students,
            'active_students': active_students,
            'monthly_registrations': monthly_registrations,
            'recent_students': recent_students,
            'university_labels': university_labels,
            'university_data': university_data,
            'total_universities': len(set(university_labels))
        }
        

        
