import secrets
from sqlalchemy.orm import Session
from . import repositories
from src.modules.email.services import EmailService

class AccountService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = repositories.UserRepository(db)
        self.student_repo = repositories.StudentRepository(db)
        self.role_repo = repositories.RoleRepository(db)
        self.email_service = EmailService(db)

    def register_student(self, user_data: dict, student_data: dict):
        """Register a new student."""
        # Check if email exists
        if self.user_repo.get_by_email(user_data['email']):
            return None

        # Generate activation token
        user_data['activation_token'] = secrets.token_urlsafe(32)
        user_data['user_type'] = 'student'

        # Create user
        user = self.user_repo.create_user(user_data)

        # Create student profile
        student_data['user_id'] = user.id
        student = self.student_repo.create_student(student_data)

        # Assign student role
        self.role_repo.assign_role(user.id, 'student')

        # Queue activation email
        self.email_service.queue_activation_email(user.id)

        return user

    def verify_credentials(self, email: str, password: str):
        """Verify user credentials."""
        user = self.user_repo.get_by_email(email)
        if user and user.password == password:  # In production, use proper password hashing
            return {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'surname': user.surname,
                'roles': [role.name for role in user.roles],
                'user_type': user.user_type,
                'department': user.student.department if user.student else None,
                'going_to': user.student.going_to if user.student else None,
                'admin_level': user.admin.admin_level if user.admin else None
            }
        return None

    def activate_account(self, token: str):
        """Activate a user account."""
        user = self.user_repo.get_by_activation_token(token)
        if user:
            self.user_repo.update_user(user.id, {
                'is_active': True,
                'activation_token': None
            })
            return True
        return False

    def get_student_details(self, user_id: int):
        """Get student details."""
        user = self.user_repo.get_by_id(user_id)
        if user and user.student:
            return {
                'id': user.id,
                'name': user.name,
                'surname': user.surname,
                'email': user.email,
                'department': user.student.department,
                'going_to': user.student.going_to,
                'is_active': user.is_active
            }
        return None

    def get_all_students(self):
        """Get all students with their details."""
        students = self.student_repo.get_all_students()
        return [{
            'id': student.user.id,
            'name': student.user.name,
            'surname': student.user.surname,
            'email': student.user.email,
            'department': student.department,
            'going_to': student.going_to,
            'is_active': student.user.is_active
        } for student in students] 