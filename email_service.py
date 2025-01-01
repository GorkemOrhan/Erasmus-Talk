import os
from sqlalchemy import create_engine
from dotenv import load_dotenv
from mail_service.mailersend import MailersendProvider
from mail_service.repository import EmailRepository
from mail_service.service import EmailService
from mail_service.scheduler import EmailScheduler

# Load environment variables
load_dotenv()

# Initialize components
db_connection_string = os.environ["DB_CONNECTION_STR"].strip('"').strip("'")
engine = create_engine(db_connection_string)

email_provider = MailersendProvider()
email_repository = EmailRepository(engine)
email_service = EmailService(email_provider, email_repository)
email_scheduler = EmailScheduler(email_service)

# Start or stop scheduler based on environment variable
if os.environ.get('SCHEDULER_ENABLED', 'false').lower() == 'true':
    email_scheduler.start()
else:
    email_scheduler.stop()

# Export functions for external use
queue_activation_email = email_repository.queue_activation_email
start_scheduler = email_scheduler.start
stop_scheduler = email_scheduler.stop
trigger_email_processing = email_scheduler.trigger_manually 