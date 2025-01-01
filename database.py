from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import json
import uuid

# Load environment variables
env = os.getenv('FLASK_ENV', 'development')
dotenv_path = f'.env.{env}'
load_dotenv(dotenv_path)

db_connection_string = os.environ["DB_CONNECTION_STR"]
db_connection_string = db_connection_string.strip('"').strip("'")
engine = create_engine(db_connection_string)

class BaseRepository:
    def __init__(self):
        self.engine = engine

class StudentRepository(BaseRepository):
    def get_all(self):
        """Get all students with their roles."""
        with self.engine.connect() as conn:
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
    
    def get_by_id(self, id):
        """Get a student by ID."""
        with self.engine.connect() as conn:
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

    def create(self, data):
        """Create a new student."""
        with self.engine.connect() as conn:
            # Check if email exists
            if UserRepository().check_email_exists(data['email']):
                return None

            # Begin transaction
            trans = conn.begin()
            try:
                # Insert base user first
                user_query = text("""
                    INSERT INTO users (
                        name, surname, email, password, user_type, activation_token
                    )
                    VALUES (
                        :name, :surname, :email, :password, 'student', :activation_token
                    )
                    RETURNING id
                """)
                result = conn.execute(user_query, {
                    "name": data['name'],
                    "surname": data['surname'],
                    "email": data['email'],
                    "password": data['password'],
                    "activation_token": data.get('activation_token')
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

                # Queue activation email
                self._queue_activation_email(conn, user_id, data)

                trans.commit()
                # Return user data including the ID
                data['id'] = user_id
                return data
            except:
                trans.rollback()
                raise

    def _queue_activation_email(self, conn, user_id, data):
        """Queue activation email for new student."""
        # Get template ID for activation email
        template_query = text("""
            SELECT id FROM mail_templates WHERE name = 'account_activation'
        """)
        template_id = conn.execute(template_query).scalar()
        
        if not template_id:
            raise ValueError("Activation email template not found")
        
        # Prepare activation URL and template data
        activation_url = f"http://localhost:5000/activate/{data['activation_token']}"
        template_data = {
            "name": data['name'],
            "activation_url": activation_url
        }

        # Queue activation email
        email_query = text("""
            INSERT INTO pending_mails (
                template_id, recipient_email, recipient_name,
                template_data, idempotency_key
            )
            VALUES (
                :template_id, :recipient_email, :recipient_name,
                :template_data, :idempotency_key
            )
        """)
        
        conn.execute(email_query, {
            "template_id": template_id,
            "recipient_email": data['email'],
            "recipient_name": data['name'],
            "template_data": json.dumps(template_data),
            "idempotency_key": str(uuid.uuid4())
        })

    def get_paginated(self, offset=0, limit=10, search=None, sort=None, order=None):
        """Get paginated list of students with search and sorting."""
        with self.engine.connect() as conn:
            # Base query
            query = """
                SELECT 
                    u.id,
                    u.name,
                    u.surname,
                    u.email,
                    s.department,
                    s.going_to,
                    u.is_active,
                    u.created_at
                FROM students s
                JOIN users u ON s.user_id = u.id
            """
            count_query = "SELECT COUNT(*) FROM students s JOIN users u ON s.user_id = u.id"
            params = {}

            # Add search condition if provided
            if search:
                search_condition = """
                    WHERE u.name ILIKE :search 
                    OR u.surname ILIKE :search 
                    OR u.email ILIKE :search 
                    OR s.department ILIKE :search
                    OR s.going_to ILIKE :search
                """
                query += search_condition
                count_query += search_condition
                params['search'] = f'%{search}%'

            # Add sorting if provided
            if sort:
                sort_column = {
                    'name': 'u.name',
                    'email': 'u.email',
                    'department': 's.department',
                    'going_to': 's.going_to',
                    'status': 'u.is_active',
                    'created_at': 'u.created_at'
                }.get(sort, 'u.created_at')
                
                query += f" ORDER BY {sort_column} {order or 'ASC'}"

            # Add pagination
            query += " LIMIT :limit OFFSET :offset"
            params.update({'limit': limit, 'offset': offset})

            # Get total count
            total = conn.execute(text(count_query), params).scalar()

            # Get paginated results
            result = conn.execute(text(query), params)
            students = []
            for row in result:
                students.append({
                    'id': row.id,
                    'name': f"{row.name} {row.surname}",
                    'email': row.email,
                    'department': row.department,
                    'going_to': row.going_to,
                    'status': 'Active' if row.is_active else 'Pending',
                    'created_at': row.created_at.strftime('%Y-%m-%d %H:%M:%S')
                })

            return {
                'total': total,
                'rows': students
            }

class UserRepository(BaseRepository):
    def check_email_exists(self, email):
        """Check if email already exists."""
        with self.engine.connect() as conn:
            query = text("SELECT COUNT(*) FROM users WHERE email = :email")
            result = conn.execute(query, {"email": email})
            count = result.scalar()
            return count > 0

    def verify_credentials(self, email, password):
        """Verify user credentials."""
        with self.engine.connect() as conn:
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
                        'role': 'admin' if user.admin_level is not None else 'student',
                        'user_type': user.user_type
                    }
                    return user_data
            return None

class DashboardRepository(BaseRepository):
    def get_stats(self):
        """Get statistics for the admin dashboard."""
        with self.engine.connect() as conn:
            # Get total students
            result = conn.execute(text("SELECT COUNT(*) FROM students"))
            total_students = result.scalar()

            # Get active students
            result = conn.execute(text("""
                SELECT COUNT(*) FROM students s
                JOIN users u ON s.user_id = u.id
                WHERE u.is_active = true
            """))
            active_students = result.scalar()

            # Get total universities
            result = conn.execute(text("SELECT COUNT(DISTINCT going_to) FROM students"))
            total_universities = result.scalar()

            # Get recent registrations (last 7 days)
            result = conn.execute(text("""
                SELECT COUNT(*) FROM students s
                JOIN users u ON s.user_id = u.id
                WHERE u.created_at >= NOW() - INTERVAL '7 days'
            """))
            recent_registrations = result.scalar()

            return {
                'total_students': total_students,
                'active_students': active_students,
                'total_universities': total_universities,
                'recent_registrations': recent_registrations
            }

# Create repository instances
student_repository = StudentRepository()
user_repository = UserRepository()
dashboard_repository = DashboardRepository()

# Export functions with the same names for backward compatibility
def load_students_from_db():
    return student_repository.get_all()

def load_student_from_db(id):
    return student_repository.get_by_id(id)
        
def add_student_to_db(data):
    return student_repository.create(data)

def verify_user_credentials(email, password):
    return user_repository.verify_credentials(email, password)

def get_dashboard_stats():
    """Get statistics for the admin dashboard."""
    return dashboard_repository.get_stats()
        

        
