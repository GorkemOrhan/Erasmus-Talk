import os
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_login import LoginManager
from config.base import BaseConfig
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.development')

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()
login_manager = LoginManager()

def create_app(config_object=BaseConfig):
    """Create Flask application."""
    app = Flask(__name__, 
                static_folder='../../static',
                template_folder='../../templates')
    
    # Configure app
    app.config.from_object(config_object)
    
    # Ensure database URI is set
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DB_CONNECTION_STR')
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app)
    login_manager.init_app(app)
    
    # Configure login manager
    login_manager.login_view = 'auth_web.login'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        from features.authentication.domain.models import User
        return User.query.get(int(user_id))
    
    @app.context_processor
    def utility_processor():
        return {
            'now': datetime.utcnow(),
            'APP_NAME': 'ErasmusTalk'
        }
    
    with app.app_context():
        # Register blueprints
        from features.authentication.web.routes import auth_web
        from features.authentication.api.v1.routes import auth_api
        
        app.register_blueprint(auth_web)
        app.register_blueprint(auth_api, url_prefix='/api/v1/auth')
        
        # Create database tables
        db.create_all()
        
        return app
