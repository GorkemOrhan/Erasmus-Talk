from flask import Flask
from src.core.database import init_db
from src.modules.account.controllers import bp as account_bp
from src.modules.email.controllers import bp as email_bp
from src.modules.email.scheduler import start_scheduler, stop_scheduler
import atexit

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__, 
                template_folder='../templates',
                static_folder='../static')

    # Load configuration
    app.config.from_object('src.config.settings')

    # Initialize database
    init_db()

    # Register blueprints
    app.register_blueprint(account_bp)
    app.register_blueprint(email_bp)

    # Start scheduler
    start_scheduler()
    atexit.register(stop_scheduler)

    return app 