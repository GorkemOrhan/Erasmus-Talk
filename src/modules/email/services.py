import json
import uuid
import requests
import jinja2
from datetime import datetime
from sqlalchemy.orm import Session
from src.config.settings import MAILGUN_API_KEY, MAILGUN_DOMAIN, MAILGUN_BASE_URL
from . import models

class EmailService:
    def __init__(self, db: Session):
        self.db = db

    def get_template(self, name: str):
        """Get email template by name."""
        return self.db.query(models.MailTemplate).filter(models.MailTemplate.name == name).first()

    def queue_email(self, template_name: str, recipient_email: str, recipient_name: str, template_data: dict):
        """Queue an email to be sent."""
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template {template_name} not found")

        pending_mail = models.PendingMail(
            template_id=template.id,
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            template_data=template_data,
            idempotency_key=str(uuid.uuid4())
        )
        
        self.db.add(pending_mail)
        self.db.commit()
        self.db.refresh(pending_mail)
        return pending_mail

    def send_email(self, pending_mail_id: int):
        """Send an email using MailGun."""
        pending_mail = self.db.query(models.PendingMail).filter(
            models.PendingMail.id == pending_mail_id,
            models.PendingMail.status == 'pending'
        ).first()

        if not pending_mail:
            return False

        # Update status to processing
        pending_mail.status = 'processing'
        pending_mail.processed_at = datetime.utcnow()
        self.db.commit()

        try:
            # Render templates
            env = jinja2.Environment()
            html_template = env.from_string(pending_mail.template.html_body)
            text_template = env.from_string(pending_mail.template.text_body) if pending_mail.template.text_body else None

            html_content = html_template.render(**pending_mail.template_data)
            text_content = text_template.render(**pending_mail.template_data) if text_template else None

            # Prepare email data
            email_data = {
                "from": f"ErasmusTalk <noreply@{MAILGUN_DOMAIN}>",
                "to": pending_mail.recipient_email,
                "subject": pending_mail.template.subject,
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
            log = models.MailLog(
                pending_mail_id=pending_mail.id,
                status='sent' if response.status_code == 200 else 'failed',
                provider_response=response.json() if response.text else None
            )

            if response.status_code == 200:
                pending_mail.status = 'sent'
            else:
                pending_mail.status = 'failed'
                pending_mail.retry_count += 1
                log.error_message = f"HTTP {response.status_code}: {response.text}"

            self.db.add(log)
            self.db.commit()
            return response.status_code == 200

        except Exception as e:
            # Log error
            log = models.MailLog(
                pending_mail_id=pending_mail.id,
                status='error',
                error_message=str(e)
            )
            self.db.add(log)
            
            # Update pending mail
            pending_mail.status = 'failed'
            pending_mail.retry_count += 1
            
            self.db.commit()
            return False

    def queue_activation_email(self, user_id: int):
        """Queue an activation email for a user."""
        user = self.db.query(models.User).filter(models.User.id == user_id).first()
        if not user or not user.activation_token:
            return False

        activation_url = f"http://localhost:5000/activate/{user.activation_token}"
        template_data = {
            "name": user.name,
            "activation_url": activation_url
        }

        return self.queue_email(
            template_name="account_activation",
            recipient_email=user.email,
            recipient_name=user.name,
            template_data=template_data
        )

    def get_email_stats(self):
        """Get email statistics."""
        stats = {
            'pending_count': self.db.query(models.PendingMail).filter(models.PendingMail.status == 'pending').count(),
            'processing_count': self.db.query(models.PendingMail).filter(models.PendingMail.status == 'processing').count(),
            'sent_count': self.db.query(models.PendingMail).filter(models.PendingMail.status == 'sent').count(),
            'failed_count': self.db.query(models.PendingMail).filter(models.PendingMail.status == 'failed').count()
        }
        stats['total_count'] = sum(stats.values())
        return stats

    def get_recent_emails(self, limit: int = 50):
        """Get recent emails with their status."""
        return self.db.query(models.PendingMail).order_by(
            models.PendingMail.created_at.desc()
        ).limit(limit).all() 