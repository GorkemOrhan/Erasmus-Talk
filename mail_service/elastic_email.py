import os
import requests
from .provider import EmailProvider

class ElasticEmailProvider(EmailProvider):
    """Elastic Email provider implementation."""
    
    def __init__(self):
        """Initialize the Elastic Email provider."""
        self.api_key = os.getenv('ELASTIC_EMAIL_API_KEY')
        self.from_email = os.getenv('EMAIL_FROM')
        self.api_url = os.getenv('ELASTIC_EMAIL_API_URL', 'https://api.elasticemail.com/v4')
        
    def send_email(self, to_email, subject, html_content, text_content=None):
        """Send an email using Elastic Email API."""
        try:
            url = f"{self.api_url}/emails/transactional"
            headers = {
                "X-ElasticEmail-ApiKey": self.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # Prepare the payload according to Elastic Email API specification
            payload = {
                "Recipients": {
                    "To": [to_email]
                },
                "Content": {
                    "From": self.from_email,
                    "Subject": subject,
                    "Html": html_content
                }
            }
            
            # Add plain text version if provided
            if text_content:
                payload["Content"]["PlainText"] = text_content
            
            # Make the API request
            response = requests.post(url, headers=headers, json=payload)
            
            
            response.raise_for_status()
            
            return True, response.json()
            
        except requests.exceptions.RequestException as e:
            error_message = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_message = error_data.get('message', str(e))
                except:
                    pass
            return False, {"error": error_message} 