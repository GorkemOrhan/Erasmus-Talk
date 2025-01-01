import os
import requests
import logging
from .provider import EmailProvider

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MailersendProvider(EmailProvider):
    """Mailersend implementation of EmailProvider."""
    
    def __init__(self):
        self.api_key = os.environ.get("MAILERSEND_API_KEY")
        self.domain = os.environ.get("MAILERSEND_DOMAIN")
        
        if not self.api_key or not self.domain:
            raise ValueError("MailerSend configuration is missing. Please set MAILERSEND_API_KEY and MAILERSEND_DOMAIN environment variables.")
        
        logger.info(f"MailerSend initialized with domain: {self.domain}")
    
    def send_email(self, to: str, subject: str, html_content: str) -> tuple[bool, str]:
        """Send email using MailerSend API."""
        try:
            logger.info(f"Attempting to send email to: {to}")
            logger.info(f"Request data: subject='{subject}', from=noreply@{self.domain}")
            
            payload = {
                "from": {
                    "email": f"noreply@{self.domain}",
                    "name": "ErasmusTalk"
                },
                "to": [
                    {
                        "email": to,
                        "name": to.split('@')[0]  # Use part before @ as name
                    }
                ],
                "subject": subject,
                "html": html_content,
                "text": ""  # Plain text version (required by MailerSend)
            }
            
            logger.info(f"Request payload: {payload}")
            
            response = requests.post(
                "https://api.mailersend.com/v1/email",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "X-Requested-With": "XMLHttpRequest"
                },
                json=payload
            )
            
            logger.info(f"Response status code: {response.status_code}")
            logger.info(f"Response body: {response.text}")
            
            if response.status_code in [200, 202]:
                return True, "Email sent successfully"
            else:
                return False, response.text
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error sending email: {error_msg}")
            return False, error_msg 