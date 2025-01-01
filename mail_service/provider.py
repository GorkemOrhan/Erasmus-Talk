from abc import ABC, abstractmethod

class EmailProvider(ABC):
    """Abstract base class for email providers."""
    
    @abstractmethod
    def send_email(self, to: str, subject: str, html_content: str) -> tuple[bool, str]:
        """Send an email and return success status and message."""
        pass 