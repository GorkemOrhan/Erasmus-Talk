import os
import json
import requests
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv
import uuid
import jinja2

# Load environment variables
load_dotenv()

# Database connection
db_connection_string = os.environ["DB_CONNECTION_STR"].strip('"').strip("'")
engine = create_engine(db_connection_string)

# MailGun configuration
MAILGUN_API_KEY = os.environ.get("MAILGUN_API_KEY")
MAILGUN_DOMAIN = os.environ.get("MAILGUN_DOMAIN")

if not MAILGUN_API_KEY or not MAILGUN_DOMAIN:
    raise ValueError("MailGun configuration is missing. Please set MAILGUN_API_KEY and MAILGUN_DOMAIN environment variables.")

MAILGUN_BASE_URL = f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}"

def queue_email(template_name, recipient_email, recipient_name, template_data):
    """Queue an email to be sent."""
    with engine.connect() as conn:
        # Begin transaction
        trans = conn.begin()
        try:
            # Get template
            template_query = text("""
                SELECT id FROM mail_templates WHERE name = :name
            """)
            template_id = conn.execute(template_query, {"name": template_name}).scalar()
            
            if not template_id:
                raise ValueError(f"Template {template_name} not found")
            
            # Create idempotency key
            idempotency_key = str(uuid.uuid4())
            
            # Insert pending mail
            query = text("""
                INSERT INTO pending_mails (
                    template_id, recipient_email, recipient_name,
                    template_data, idempotency_key
                )
                VALUES (
                    :template_id, :recipient_email, :recipient_name,
                    :template_data, :idempotency_key
                )
            """)
            
            conn.execute(query, {
                "template_id": template_id,
                "recipient_email": recipient_email,
                "recipient_name": recipient_name,
                "template_data": json.dumps(template_data),
                "idempotency_key": idempotency_key
            })
            
            trans.commit()
            return True
        except:
            trans.rollback()
            raise

def send_email(pending_mail_id):
    """Send an email using MailGun."""
    with engine.connect() as conn:
        # Begin transaction
        trans = conn.begin()
        try:
            # Get pending mail with template
            query = text("""
                SELECT 
                    pm.*,
                    mt.subject,
                    mt.html_body,
                    mt.text_body
                FROM pending_mails pm
                JOIN mail_templates mt ON pm.template_id = mt.id
                WHERE pm.id = :id AND pm.status = 'pending'
                FOR UPDATE
            """)
            
            result = conn.execute(query, {"id": pending_mail_id}).fetchone()
            if not result:
                return False
            
            # Update status to processing
            update_query = text("""
                UPDATE pending_mails
                SET status = 'processing', processed_at = NOW()
                WHERE id = :id
            """)
            conn.execute(update_query, {"id": pending_mail_id})
            
            # Prepare template data
            template_data = json.loads(result.template_data)
            
            # Render templates
            env = jinja2.Environment()
            html_template = env.from_string(result.html_body)
            text_template = env.from_string(result.text_body) if result.text_body else None
            
            html_content = html_template.render(**template_data)
            text_content = text_template.render(**template_data) if text_template else None
            
            # Prepare email data
            email_data = {
                "from": f"ErasmusTalk <noreply@{MAILGUN_DOMAIN}>",
                "to": result.recipient_email,
                "subject": result.subject,
                "html": html_content
            }
            if text_content:
                email_data["text"] = text_content
            
            # Send email via MailGun
            response = requests.post(
                f"{MAILGUN_BASE_URL}/messages",
                auth=("api", MAILGUN_API_KEY),
                data=email_data
            )
            
            # Log the attempt
            log_query = text("""
                INSERT INTO mail_logs (
                    pending_mail_id, status, provider_response
                )
                VALUES (
                    :pending_mail_id, :status, :provider_response
                )
            """)
            
            if response.status_code == 200:
                # Update pending_mail status to sent
                status_query = text("""
                    UPDATE pending_mails
                    SET status = 'sent'
                    WHERE id = :id
                """)
                conn.execute(status_query, {"id": pending_mail_id})
                
                # Log success
                conn.execute(log_query, {
                    "pending_mail_id": pending_mail_id,
                    "status": "sent",
                    "provider_response": json.dumps(response.json())
                })
            else:
                # Update pending_mail for retry
                retry_query = text("""
                    UPDATE pending_mails
                    SET 
                        status = 'failed',
                        retry_count = retry_count + 1,
                        next_retry_at = CASE
                            WHEN retry_count < 3 THEN NOW() + interval '5 minutes'
                            WHEN retry_count < 5 THEN NOW() + interval '30 minutes'
                            ELSE NULL
                        END
                    WHERE id = :id
                """)
                conn.execute(retry_query, {"id": pending_mail_id})
                
                # Log error
                conn.execute(log_query, {
                    "pending_mail_id": pending_mail_id,
                    "status": "failed",
                    "error_message": f"HTTP {response.status_code}: {response.text}",
                    "provider_response": json.dumps(response.json() if response.text else None)
                })
            
            trans.commit()
            return response.status_code == 200
        except Exception as e:
            trans.rollback()
            # Log unexpected error
            error_log_query = text("""
                INSERT INTO mail_logs (
                    pending_mail_id, status, error_message
                )
                VALUES (
                    :pending_mail_id, 'error', :error_message
                )
            """)
            conn.execute(error_log_query, {
                "pending_mail_id": pending_mail_id,
                "error_message": str(e)
            })
            conn.commit()
            raise

def process_pending_emails():
    """Process all pending emails."""
    with engine.connect() as conn:
        # Get pending emails ready for processing
        query = text("""
            SELECT id
            FROM pending_mails
            WHERE 
                status IN ('pending', 'failed')
                AND (next_retry_at IS NULL OR next_retry_at <= NOW())
                AND (retry_count < 5)
            ORDER BY created_at
            LIMIT 10
        """)
        
        pending_mails = conn.execute(query).fetchall()
        
        for mail in pending_mails:
            try:
                send_email(mail.id)
            except Exception as e:
                print(f"Error processing mail {mail.id}: {str(e)}")

# Initialize scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(
    process_pending_emails,
    trigger=IntervalTrigger(seconds=10),
    id='process_emails',
    name='Process pending emails every 10 seconds',
    replace_existing=True
)

def start_scheduler():
    """Start the email processing scheduler."""
    if not scheduler.running:
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

# Helper function to queue activation email
def queue_activation_email(user_id):
    """Queue an activation email for a user."""
    with engine.connect() as conn:
        # Get user details
        query = text("""
            SELECT name, email, activation_token
            FROM users
            WHERE id = :id
        """)
        user = conn.execute(query, {"id": user_id}).fetchone()
        
        if not user or not user.activation_token:
            return False
        
        # Queue activation email
        activation_url = f"http://localhost:5000/activate/{user.activation_token}"
        template_data = {
            "name": user.name,
            "activation_url": activation_url
        }
        
        return queue_email(
            template_name="account_activation",
            recipient_email=user.email,
            recipient_name=user.name,
            template_data=template_data
        ) 