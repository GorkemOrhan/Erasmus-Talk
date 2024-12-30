from sqlalchemy.orm import Session
from sqlalchemy import text
from . import models

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int):
        return self.db.query(models.User).filter(models.User.id == user_id).first()

    def get_by_email(self, email: str):
        return self.db.query(models.User).filter(models.User.email == email).first()

    def get_by_activation_token(self, token: str):
        return self.db.query(models.User).filter(models.User.activation_token == token).first()

    def create_user(self, user_data: dict):
        user = models.User(**user_data)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_user(self, user_id: int, user_data: dict):
        user = self.get_by_id(user_id)
        if user:
            for key, value in user_data.items():
                setattr(user, key, value)
            self.db.commit()
            self.db.refresh(user)
        return user

    def delete_user(self, user_id: int):
        user = self.get_by_id(user_id)
        if user:
            self.db.delete(user)
            self.db.commit()
            return True
        return False

class StudentRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_all_students(self):
        return self.db.query(models.Student).all()

    def get_by_user_id(self, user_id: int):
        return self.db.query(models.Student).filter(models.Student.user_id == user_id).first()

    def create_student(self, student_data: dict):
        student = models.Student(**student_data)
        self.db.add(student)
        self.db.commit()
        self.db.refresh(student)
        return student

    def update_student(self, user_id: int, student_data: dict):
        student = self.get_by_user_id(user_id)
        if student:
            for key, value in student_data.items():
                setattr(student, key, value)
            self.db.commit()
            self.db.refresh(student)
        return student

class RoleRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_name(self, name: str):
        return self.db.query(models.Role).filter(models.Role.name == name).first()

    def assign_role(self, user_id: int, role_name: str):
        role = self.get_by_name(role_name)
        if role:
            user = self.db.query(models.User).filter(models.User.id == user_id).first()
            if user:
                user.roles.append(role)
                self.db.commit()
                return True
        return False 