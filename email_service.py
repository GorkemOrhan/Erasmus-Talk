import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import requests
import json

# Load environment variables
load_dotenv()

def send_email(to_email, subject, template_name, template_data):
    """Send an email using Elastic Email."""
    try:
        # Get database connection
        engine = create_engine(os.getenv('DB_CONNECTION_STR'))
        
        with engine.connect() as conn:
            # Get template from database
            query = text("""
                SELECT html_body 
                FROM mail_templates 
                WHERE name = :template_name
            """)
            result = conn.execute(query, {"template_name": template_name}).fetchone()
            
            if not result:
                raise ValueError(f"Template {template_name} not found")
            
            # Replace template variables
            html_content = result[0]
            for key, value in template_data.items():
                html_content = html_content.replace('{{' + key + '}}', str(value))
            
            # Prepare Elastic Email API request
            url = "https://api.elasticemail.com/v4/emails/transactional"
            headers = {
                "X-ElasticEmail-ApiKey": os.getenv('ELASTIC_EMAIL_API_KEY'),
                "Content-Type": "application/json"
            }
            
            payload = {
                "Recipients": {
                    "To": [to_email]
                },
                "Content": {
                    "Body": [
                        {
                            "ContentType": "HTML",
                            "Content": html_content
                        }
                    ],
                    "Subject": subject,
                    "From": os.getenv('EMAIL_FROM')
                }
            }
            
            # Send email via Elastic Email API
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            return True, None
            
    except Exception as e:
        error_message = str(e)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_data = e.response.json()
                error_message = error_data.get('message', str(e))
            except:
                pass
        return False, error_message

def queue_activation_email(user_email, user_name, activation_url):
    """Queue an activation email to be sent."""
    try:
        engine = create_engine(os.getenv('DB_CONNECTION_STR'))
        
        with engine.connect() as conn:
            # Get template ID
            template_query = text("""
                SELECT id FROM mail_templates 
                WHERE name = 'account_activation'
            """)
            template_id = conn.execute(template_query).fetchone()[0]
            
            # Queue email
            insert_query = text("""
                INSERT INTO pending_mails (
                    template_id, recipient_email, recipient_name,
                    template_data, status
                ) VALUES (
                    :template_id, :recipient_email, :recipient_name,
                    :template_data, 'pending'
                )
            """)
            
            template_data = {
                "name": user_name,
                "activation_url": activation_url
            }
            
            conn.execute(insert_query, {
                "template_id": template_id,
                "recipient_email": user_email,
                "recipient_name": user_name,
                "template_data": json.dumps(template_data)
            })
            
            conn.commit()
            return True, None
            
    except Exception as e:
        return False, str(e)

def start_scheduler():
    """Start the email processing scheduler."""
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    from mail_service.scheduler import process_pending_emails
    
    if os.getenv('SCHEDULER_ENABLED', 'false').lower() == 'true':
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            func=process_pending_emails,
            trigger=IntervalTrigger(seconds=30),
            id='process_emails',
            name='Process pending emails',
            replace_existing=True
        )
        scheduler.start()
        return scheduler
    return None

def stop_scheduler():
    """Stop the email processing scheduler."""
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler()
    scheduler.shutdown()

def trigger_email_processing():
    """Manually trigger email processing."""
    try:
        from mail_service.scheduler import process_pending_emails
        success, message = process_pending_emails()
        if success:
            return True, "Email processing triggered successfully"
        return False, f"Error processing emails: {message}"
    except Exception as e:
        return False, str(e) 