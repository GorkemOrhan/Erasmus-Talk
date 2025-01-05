from datetime import datetime
from app.factory import db
import bcrypt
from flask_login import UserMixin

class User(UserMixin, db.Model):
    """User model for storing user credentials and profile data."""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    _password = db.Column('password', db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=False)
    activation_token = db.Column(db.String(255))
    user_type = db.Column(db.String(20), nullable=False)
    
    def __init__(self, email, password, name, surname, user_type='student'):
        self.email = email
        self.password = password  # This will call the password.setter
        self.name = name
        self.surname = surname
        self.user_type = user_type
    
    @property
    def password(self):
        return self._password
    
    @password.setter
    def password(self, password):
        salt = bcrypt.gensalt()
        self._password = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self._password.encode('utf-8'))
    
    @property
    def full_name(self):
        if self.name and self.surname:
            return f"{self.name} {self.surname}"
        return self.email
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'surname': self.surname,
            'is_active': self.is_active,
            'user_type': self.user_type,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class ActivationToken(db.Model):
    """Model for storing account activation tokens."""
    
    __tablename__ = 'activation_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    
    user = db.relationship('User', backref=db.backref('activation_tokens', lazy=True))

class PasswordResetToken(db.Model):
    """Model for storing password reset tokens."""
    
    __tablename__ = 'password_reset_tokens'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    
    user = db.relationship('User', backref=db.backref('password_reset_tokens', lazy=True)) 