from sqlalchemy import text
import uuid
import json

class EmailRepository:
    """Repository for email-related database operations."""
    
    def __init__(self, engine):
        self.engine = engine
    
    def get_pending_emails(self, limit: int = 10):
        """Get pending emails that need to be sent."""
        query = text("""
            SELECT pm.*, mt.html_body as template_body
            FROM pending_mails pm
            JOIN mail_templates mt ON pm.template_id = mt.id
            WHERE pm.status = 'pending'
            AND (pm.next_retry_at IS NULL OR pm.next_retry_at <= NOW())
            LIMIT :limit
        """)
        with self.engine.connect() as conn:
            return conn.execute(query, {"limit": limit}).fetchall()
    
    def update_email_status(self, email_id: int, status: str, error_message: str = None):
        """Update email status and handle retries."""
        if status == 'sent':
            query = text("""
                UPDATE pending_mails
                SET status = 'sent'
                WHERE id = :id
            """)
            params = {"id": email_id}
        else:
            query = text("""
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
            params = {"id": email_id}
        
        with self.engine.connect() as conn:
            conn.execute(query, params)
            
            # Log the status
            log_query = text("""
                INSERT INTO mail_logs (pending_mail_id, status, error_message)
                VALUES (:pending_mail_id, :status, :error_message)
            """)
            conn.execute(log_query, {
                "pending_mail_id": email_id,
                "status": status,
                "error_message": error_message
            })
            conn.commit()
            
    def queue_activation_email(self, user_id: int) -> bool:
        """Queue an activation email for a user."""
        with self.engine.connect() as conn:
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
            
            # Queue email
            query = text("""
                INSERT INTO pending_mails (
                    template_id, recipient_email, recipient_name,
                    template_data, status, idempotency_key
                )
                VALUES (
                    (SELECT id FROM mail_templates WHERE name = :template_name),
                    :recipient_email, :recipient_name,
                    :template_data, 'pending', :idempotency_key
                )
            """)
            
            try:
                conn.execute(query, {
                    "template_name": "account_activation",
                    "recipient_email": user.email,
                    "recipient_name": user.name,
                    "template_data": json.dumps(template_data),
                    "idempotency_key": str(uuid.uuid4())
                })
                conn.commit()
                return True
            except Exception as e:
                print(f"Error queueing activation email: {str(e)}")
                return False 