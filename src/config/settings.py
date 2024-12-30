import os
from dotenv import load_dotenv

# Load environment variables
env = os.getenv('FLASK_ENV', 'development')
dotenv_path = f'.env.{env}'
load_dotenv(dotenv_path)

# Database Configuration
DB_CONNECTION_STR = os.environ.get("DB_CONNECTION_STR").strip('"').strip("'")

# Flask Configuration
SECRET_KEY = os.environ.get('SECRET_KEY', os.urandom(24))
JWT_SECRET = os.environ.get('JWT_SECRET', os.urandom(24))

# MailGun Configuration
MAILGUN_API_KEY = os.environ.get("MAILGUN_API_KEY")
MAILGUN_DOMAIN = os.environ.get("MAILGUN_DOMAIN")
MAILGUN_BASE_URL = f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}"

# Scheduler Configuration
SCHEDULER_ENABLED = os.environ.get('SCHEDULER_ENABLED', 'false').lower() == 'true' 