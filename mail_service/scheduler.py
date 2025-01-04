import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
import json
import requests

def process_pending_emails():
    """Process all pending emails."""
    try:
        engine = create_engine(os.getenv('DB_CONNECTION_STR'))
        
        with engine.connect() as conn:
            # Get pending emails
            query = text("""
                SELECT 
                    pm.id,
                    pm.recipient_email,
                    pm.recipient_name,
                    pm.template_data,
                    mt.name as template_name,
                    mt.subject,
                    mt.html_body
                FROM pending_mails pm
                JOIN mail_templates mt ON pm.template_id = mt.id
                WHERE pm.status = 'pending'
                AND (pm.next_retry_at IS NULL OR pm.next_retry_at <= NOW())
                LIMIT 10
            """)
            
            pending_emails = conn.execute(query).fetchall()
            print(f"Found {len(pending_emails)} pending emails to process")
            
            for email in pending_emails:
                try:
                    print(f"Processing email {email.id} to {email.recipient_email}")
                    
                    # Mark as processing
                    update_query = text("""
                        UPDATE pending_mails 
                        SET status = 'processing', 
                            processed_at = NOW()
                        WHERE id = :id
                    """)
                    conn.execute(update_query, {"id": email.id})
                    conn.commit()
                    
                    # Parse template data
                    template_data = json.loads(email.template_data) if isinstance(email.template_data, str) else email.template_data
                    
                    # Replace template variables
                    html_content = email.html_body
                    for key, value in template_data.items():
                        html_content = html_content.replace('{{' + key + '}}', str(value))
                    
                    # Send email using Elastic Email API
                    url = f"{os.getenv('ELASTIC_EMAIL_API_URL', 'https://api.elasticemail.com/v4')}/emails/transactional"
                    headers = {
                        "X-ElasticEmail-ApiKey": os.getenv('ELASTIC_EMAIL_API_KEY'),
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    }
                    
                    payload = {
                        "Recipients": {
                            "To": [email.recipient_email]
                        },
                        "Content": {
                            "From": os.getenv('EMAIL_FROM'),
                            "Subject": email.subject,
                            "Html": html_content
                        }
                    }
                    
                    print(f"Sending request to Elastic Email API: {url}")
                    print(f"Payload: {payload}")
                    
                    response = requests.post(url, headers=headers, json=payload)
                    print(f"API Response: {response.status_code} - {response.text}")
                    
                    if response.status_code == 200:
                        # Mark as sent
                        success_query = text("""
                            UPDATE pending_mails 
                            SET status = 'sent', 
                                processed_at = NOW()
                            WHERE id = :id
                        """)
                        conn.execute(success_query, {"id": email.id})
                        
                        # Log success
                        log_query = text("""
                            INSERT INTO mail_logs (
                                pending_mail_id, status, provider_response
                            ) VALUES (
                                :mail_id, 'sent', :response
                            )
                        """)
                        conn.execute(log_query, {
                            "mail_id": email.id,
                            "response": json.dumps(response.json())
                        })
                    else:
                        raise Exception(f"API Error: {response.text}")
                    
                except Exception as e:
                    print(f"Error processing email {email.id}: {str(e)}")
                    
                    # Handle failure
                    error_message = str(e)
                    if hasattr(e, 'response') and e.response is not None:
                        try:
                            error_data = e.response.json()
                            error_message = error_data.get('message', str(e))
                        except:
                            pass
                    
                    # Update email status
                    retry_count_query = text("""
                        UPDATE pending_mails 
                        SET status = 'failed',
                            retry_count = retry_count + 1,
                            next_retry_at = CASE 
                                WHEN retry_count < 3 THEN NOW() + interval '5 minutes'
                                ELSE NULL
                            END,
                            processed_at = NOW()
                        WHERE id = :id
                        RETURNING retry_count
                    """)
                    conn.execute(retry_count_query, {"id": email.id})
                    
                    # Log error
                    log_query = text("""
                        INSERT INTO mail_logs (
                            pending_mail_id, status, error_message
                        ) VALUES (
                            :mail_id, 'failed', :error
                        )
                    """)
                    conn.execute(log_query, {
                        "mail_id": email.id,
                        "error": error_message
                    })
                
                conn.commit()
            
            return True, "Emails processed successfully"
            
    except Exception as e:
        print(f"Error in process_pending_emails: {str(e)}")
        return False, str(e) 