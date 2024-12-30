from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from src.config.settings import SCHEDULER_ENABLED
from src.core.database import SessionLocal
from . import services

scheduler = BackgroundScheduler()

def process_pending_emails():
    """Process all pending emails."""
    db = SessionLocal()
    try:
        email_service = services.EmailService(db)
        pending_mails = db.query(services.models.PendingMail).filter(
            services.models.PendingMail.status.in_(['pending', 'failed']),
            services.models.PendingMail.retry_count < 5
        ).order_by(services.models.PendingMail.created_at).limit(10).all()

        for mail in pending_mails:
            try:
                email_service.send_email(mail.id)
            except Exception as e:
                print(f"Error processing mail {mail.id}: {str(e)}")
    finally:
        db.close()

# Add job to scheduler
scheduler.add_job(
    process_pending_emails,
    trigger=IntervalTrigger(seconds=10),
    id='process_emails',
    name='Process pending emails every 10 seconds',
    replace_existing=True
)

def start_scheduler():
    """Start the email processing scheduler if enabled."""
    if SCHEDULER_ENABLED and not scheduler.running:
        scheduler.start()

def stop_scheduler():
    """Stop the email processing scheduler."""
    if scheduler.running:
        scheduler.shutdown()

def trigger_email_processing():
    """Manually trigger email processing."""
    try:
        process_pending_emails()
        return True, "Email processing triggered successfully"
    except Exception as e:
        return False, f"Error processing emails: {str(e)}" 