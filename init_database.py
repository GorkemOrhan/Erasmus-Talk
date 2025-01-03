from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
import traceback

def mask_connection_string(conn_str):
    # Mask sensitive information in connection string for safe logging
    if not conn_str:
        return "None"
    parts = conn_str.split('@')
    if len(parts) > 1:
        credentials = parts[0].split(':')
        if len(credentials) > 2:
            masked = f"{credentials[0]}:****:****@{parts[1]}"
            return masked
    return "Invalid connection string format"

# Load environment variables
env = os.getenv('FLASK_ENV', 'development')
dotenv_path = f'.env.{env}'
print(f"Loading environment from: {dotenv_path}")

load_dotenv(dotenv_path)

# Get and verify database connection string
db_connection_string = os.environ.get("DB_CONNECTION_STR")
if not db_connection_string:
    print("ERROR: DB_CONNECTION_STR not found in environment variables")
    exit(1)

db_connection_string = db_connection_string.strip('"').strip("'")
print(f"Using connection string: {mask_connection_string(db_connection_string)}")

# Define HTML templates as separate variables with proper escaping
activation_html_template = '''
<!DOCTYPE html>
<html>
<body>
    <h2>Welcome to ErasmusTalk!</h2>
    <p>Dear {{name}},</p>
    <p>Thank you for joining ErasmusTalk. To activate your account, please click the button below:</p>
    <p>
        <a href="{{activation_url}}" style="background-color: #4e73df; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
            Activate Account
        </a>
    </p>
    <p>Or copy and paste this link in your browser:</p>
    <p>{{activation_url}}</p>
    <p>This link will expire in 24 hours.</p>
    <p>Best regards,<br>The ErasmusTalk Team</p>
</body>
</html>
'''.strip()

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

# Create SQL statements list
sql_statements = [
    "SET search_path TO public",
    
    # Enable pgcrypto extension
    "CREATE EXTENSION IF NOT EXISTS pgcrypto",
    
    # Drop tables
    "DROP TABLE IF EXISTS public.mail_logs CASCADE",
    "DROP TABLE IF EXISTS public.pending_mails CASCADE",
    "DROP TABLE IF EXISTS public.mail_templates CASCADE",
    "DROP TABLE IF EXISTS public.password_reset_tokens CASCADE",
    "DROP TABLE IF EXISTS public.profiles CASCADE",
    "DROP TABLE IF EXISTS public.user_roles CASCADE",
    "DROP TABLE IF EXISTS public.admins CASCADE",
    "DROP TABLE IF EXISTS public.students CASCADE",
    "DROP TABLE IF EXISTS public.users CASCADE",
    "DROP TABLE IF EXISTS public.roles CASCADE",
    
    # Create tables
    """CREATE TABLE public.roles (
        id SERIAL PRIMARY KEY,
        name VARCHAR(50) NOT NULL UNIQUE,
        description TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    )""",
    
    """CREATE TABLE public.users (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        surname VARCHAR(100) NOT NULL,
        email VARCHAR(255) NOT NULL UNIQUE,
        password VARCHAR(255) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        is_active BOOLEAN DEFAULT FALSE,
        activation_token VARCHAR(255),
        user_type VARCHAR(20) NOT NULL
    )""",
    
    """CREATE TABLE public.students (
        user_id INTEGER PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
        department VARCHAR(100) NOT NULL,
        going_to VARCHAR(255) NOT NULL
    )""",
    
    """CREATE TABLE public.admins (
        user_id INTEGER PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
        admin_level INTEGER DEFAULT 1
    )""",
    
    """CREATE TABLE public.user_roles (
        user_id INTEGER REFERENCES public.users(id) ON DELETE CASCADE,
        role_id INTEGER REFERENCES public.roles(id) ON DELETE CASCADE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, role_id)
    )""",
    
    """CREATE TABLE public.profiles (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES public.users(id) ON DELETE CASCADE,
        bio TEXT,
        avatar_url VARCHAR(255),
        social_links JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    )""",
    
    """CREATE TABLE public.password_reset_tokens (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES public.users(id) ON DELETE CASCADE,
        token VARCHAR(255) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
        used BOOLEAN DEFAULT FALSE
    )""",
    
    """CREATE TABLE public.mail_templates (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) NOT NULL UNIQUE,
        subject VARCHAR(255) NOT NULL,
        html_body TEXT NOT NULL,
        text_body TEXT,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    )""",
    
    """CREATE TABLE public.pending_mails (
        id SERIAL PRIMARY KEY,
        template_id INTEGER REFERENCES public.mail_templates(id),
        recipient_email VARCHAR(255) NOT NULL,
        recipient_name VARCHAR(255),
        template_data JSONB,
        status VARCHAR(50) DEFAULT 'pending',
        retry_count INTEGER DEFAULT 0,
        next_retry_at TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        processed_at TIMESTAMP WITH TIME ZONE,
        idempotency_key VARCHAR(255) UNIQUE,
        CONSTRAINT valid_status CHECK (status IN ('pending', 'processing', 'sent', 'failed'))
    )""",
    
    """CREATE TABLE public.mail_logs (
        id SERIAL PRIMARY KEY,
        pending_mail_id INTEGER REFERENCES public.pending_mails(id),
        status VARCHAR(50) NOT NULL,
        error_message TEXT,
        provider_response JSONB,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    )""",
    
    # Insert initial data
    """INSERT INTO public.roles (name, description) VALUES
        ('admin', 'Administrator with full system access'),
        ('student', 'Regular student user')""",
    
    """WITH new_user AS (
        INSERT INTO public.users (name, surname, email, password, is_active, user_type)
        VALUES ('Admin', 'User', 'admin@erasmustalk.com', 'admin123', true, 'admin')
        RETURNING id
    )
    INSERT INTO public.admins (user_id, admin_level)
    SELECT id, 1 FROM new_user""",
    
    """INSERT INTO public.user_roles (user_id, role_id)
    SELECT u.id, r.id
    FROM public.users u, public.roles r
    WHERE u.email = 'admin@erasmustalk.com' AND r.name = 'admin'""",
    
    """CREATE OR REPLACE VIEW public.all_users AS
        SELECT
            u.*,
            s.department,
            s.going_to,
            a.admin_level
        FROM public.users u
        LEFT JOIN public.students s ON u.id = s.user_id
        LEFT JOIN public.admins a ON u.id = a.user_id""",
        
    """INSERT INTO mail_templates (name, subject, html_body)
    VALUES 
        ('account_activation', 'Welcome to ErasmusTalk - Activate Your Account', :activation_template),
        ('password_reset', 'Password Reset Request - ErasmusTalk', :password_template)
    ON CONFLICT (name) DO UPDATE 
    SET html_body = EXCLUDED.html_body,
        subject = EXCLUDED.subject"""
]

try:
    print("Creating database engine...")
    engine = create_engine(db_connection_string, echo=True)
    
    print("Attempting to connect to database...")
    with engine.connect() as conn:
        print("Connected successfully. Creating tables...")
        
        # Execute all statements
        for i, statement in enumerate(sql_statements[:-1], 1):  # Execute all except the last one normally
            print(f"Executing statement {i}/{len(sql_statements)}...")
            conn.execute(text(statement))
            print(f"Statement {i} executed successfully")
        
        # Execute the last statement (template insertion) with parameters
        print(f"Executing statement {len(sql_statements)}/{len(sql_statements)}...")
        conn.execute(text(sql_statements[-1]), {
            "activation_template": activation_html_template,
            "password_template": password_reset_html_template
        })
        print(f"Statement {len(sql_statements)} executed successfully")
        
        # Check if templates exist
        template_query = text("SELECT name, subject FROM mail_templates")
        templates = conn.execute(template_query).fetchall()
        print("\nExisting email templates:")
        print("-" * 50)
        for template in templates:
            print(f"- {template[0]}: {template[1]}")
        
        conn.commit()
        print("Database tables created successfully!")

except Exception as e:
    print("\nERROR DETAILS:")
    print("=" * 50)
    print(f"Error Type: {type(e).__name__}")
    print(f"Error Message: {str(e)}")
    print("\nFull Traceback:")
    print(traceback.format_exc())
    print("=" * 50)
    raise 