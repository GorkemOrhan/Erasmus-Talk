from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

env = os.getenv('FLASK_ENV', 'development')
dotenv_path = f'.env.{env}'
load_dotenv(dotenv_path)

db_connection_string = os.environ["DB_CONNECTION_STR"]
db_connection_string = db_connection_string.strip('"').strip("'")

engine = create_engine(db_connection_string)

check_tables_sql = """
SELECT table_name, table_schema
FROM information_schema.tables 
WHERE table_schema = 'public'
AND table_type = 'BASE TABLE'
ORDER BY table_schema, table_name;
"""

# Create password reset tokens table
create_password_reset_tokens_table = """
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    token VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE,
    CONSTRAINT fk_user
        FOREIGN KEY(user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
);
"""

# Password reset email template
password_reset_html_template = '''
<!DOCTYPE html>
<html>
<body>
    <h2>Password Reset Request - ErasmusTalk</h2>
    <p>Dear {{name}},</p>
    <p>We received a request to reset your password. Click the button below to create a new password:</p>
    <p>
        <a href="{{reset_url}}" style="background-color: #4e73df; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
            Reset Password
        </a>
    </p>
    <p>Or copy and paste this link in your browser:</p>
    <p>{{reset_url}}</p>
    <p>This link will expire in 1 hour. If you didn't request this password reset, please ignore this email.</p>
    <p>Best regards,<br>The ErasmusTalk Team</p>
</body>
</html>
'''.strip()

try:
    with engine.connect() as conn:
        result = conn.execute(text(check_tables_sql))
        tables = result.fetchall()
        
        print("\nExisting tables in database:")
        print("=" * 50)
        print("Schema  |  Table Name")
        print("-" * 50)
        for table in tables:
            print(f"{table[1]}  |  {table[0]}")
            
        # Check specific tables
        expected_tables = {'students', 'profiles', 'password_reset_tokens', 'mail_templates', 'pending_mails', 'mail_logs', 'users'}
        existing_tables = {table[0] for table in tables}
        missing_tables = expected_tables - existing_tables
        
        if missing_tables:
            print("\nMissing tables:")
            for table in missing_tables:
                print(f"- {table}")
        else:
            print("\nAll required tables exist in public schema!")
            
        # Create tables
        conn.execute(text(create_password_reset_tokens_table))
        
        # Insert password reset email template if it doesn't exist
        insert_template_query = text("""
            INSERT INTO mail_templates (name, html_body)
            VALUES ('password_reset', :template)
            ON CONFLICT (name) DO UPDATE 
            SET html_body = :template
        """)
        conn.execute(insert_template_query, {"template": password_reset_html_template})
        conn.commit()
        
except Exception as e:
    print(f"Error checking tables: {str(e)}") 