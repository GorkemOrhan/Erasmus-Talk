from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config.base import BaseConfig

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()

def create_app(config_object=BaseConfig):
    """Create Flask application."""
    app = Flask(__name__, 
                static_folder='../static',
                template_folder='../templates')
    
    # Configure app
    app.config.from_object(config_object)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app)
    
    with app.app_context():
        # Register blueprints
        from features.authentication.web.routes import auth_web
        from features.authentication.api.v1.routes import auth_api
        
        app.register_blueprint(auth_web)
        app.register_blueprint(auth_api, url_prefix='/api/v1/auth')
        
        # Create database tables
        db.create_all()
        
        return app 