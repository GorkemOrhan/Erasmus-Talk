from jinja2 import Template
from .provider import EmailProvider
from .repository import EmailRepository

class EmailService:
    """Service for handling email operations."""
    
    def __init__(self, email_provider: EmailProvider, email_repository: EmailRepository):
        self.email_provider = email_provider
        self.email_repository = email_repository
    
    def process_pending_emails(self):
        """Process all pending emails."""
        pending_emails = self.email_repository.get_pending_emails()
        
        for email in pending_emails:
            try:
                # Render template
                template = Template(email.template_body)
                html = template.render(**email.template_data)
                
                # Send email
                success, message = self.email_provider.send_email(
                    to=email.recipient_email,
                    subject="Welcome to ErasmusTalk - Activate Your Account",
                    html_content=html
                )
                
                # Update status
                status = 'sent' if success else 'failed'
                self.email_repository.update_email_status(
                    email_id=email.id,
                    status=status,
                    error_message=None if success else message
                )
            except Exception as e:
                print(f"Error processing email {email.id}: {str(e)}")
                self.email_repository.update_email_status(
                    email_id=email.id,
                    status='failed',
                    error_message=str(e)
                ) 