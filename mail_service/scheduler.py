import os
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from .service import EmailService

class EmailScheduler:
    """Handles scheduling of email processing."""
    
    def __init__(self, email_service: EmailService):
        self.email_service = email_service
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(
            self.email_service.process_pending_emails,
            trigger=IntervalTrigger(seconds=10),
            id='process_emails',
            name='Process pending emails every 10 seconds',
            replace_existing=True
        )
    
    def start(self):
        """Start the scheduler if enabled."""
        if os.environ.get('SCHEDULER_ENABLED', 'false').lower() == 'true':
            if not self.scheduler.running:
                self.scheduler.start()
    
    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
    
    def trigger_manually(self) -> tuple[bool, str]:
        """Manually trigger email processing."""
        try:
            self.email_service.process_pending_emails()
            return True, "Email processing triggered successfully"
        except Exception as e:
            return False, f"Error processing emails: {str(e)}" 