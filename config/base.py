import os
from datetime import timedelta

class BaseConfig:
    """Base configuration."""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24))
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', os.urandom(24))
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv('DB_CONNECTION_STR')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # Email
    EMAIL_PROVIDER = os.getenv('EMAIL_PROVIDER', 'elastic_email')
    EMAIL_API_KEY = os.getenv('ELASTIC_EMAIL_API_KEY')
    EMAIL_DOMAIN = os.getenv('EMAIL_DOMAIN')
    EMAIL_FROM = os.getenv('EMAIL_FROM')
    EMAIL_API_URL = os.getenv('ELASTIC_EMAIL_API_URL', 'https://api.elasticemail.com/v4')
    
    # App
    APP_NAME = "ErasmusTalk"
    APP_URL = os.getenv('APP_URL', 'http://localhost:5000') 