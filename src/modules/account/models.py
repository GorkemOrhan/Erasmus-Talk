from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from src.core.database import Base

# Association table for user roles
user_roles = Table('user_roles',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True)
)

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    surname = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=False)
    activation_token = Column(String(255))
    user_type = Column(String(20), nullable=False)  # 'admin' or 'student'

    # Relationships
    roles = relationship('Role', secondary=user_roles, back_populates='users')
    student = relationship('Student', back_populates='user', uselist=False)
    admin = relationship('Admin', back_populates='user', uselist=False)

class Role(Base):
    __tablename__ = 'roles'

    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    users = relationship('User', secondary=user_roles, back_populates='roles')

class Student(Base):
    __tablename__ = 'students'

    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    department = Column(String(100), nullable=False)
    going_to = Column(String(255), nullable=False)

    # Relationships
    user = relationship('User', back_populates='student')

class Admin(Base):
    __tablename__ = 'admins'

    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    admin_level = Column(Integer, default=1)

    # Relationships
    user = relationship('User', back_populates='admin') 