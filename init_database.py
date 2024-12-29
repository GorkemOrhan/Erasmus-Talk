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

# SQL to create tables
create_tables_sql = """
-- Ensure we're using the public schema
SET search_path TO public;

-- First, drop all existing tables in the correct order
DROP TABLE IF EXISTS public.password_reset_tokens CASCADE;
DROP TABLE IF EXISTS public.profiles CASCADE;
DROP TABLE IF EXISTS public.user_roles CASCADE;
DROP TABLE IF EXISTS public.admins CASCADE;
DROP TABLE IF EXISTS public.students CASCADE;
DROP TABLE IF EXISTS public.users CASCADE;
DROP TABLE IF EXISTS public.roles CASCADE;

-- Create roles table
CREATE TABLE public.roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create base users table with common attributes
CREATE TABLE public.users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    surname VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT FALSE,
    activation_token VARCHAR(255),
    user_type VARCHAR(20) NOT NULL  -- 'admin' or 'student'
);

-- Create students table that extends users
CREATE TABLE public.students (
    user_id INTEGER PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
    department VARCHAR(100) NOT NULL,
    going_to VARCHAR(255) NOT NULL
);

-- Create admins table that extends users
CREATE TABLE public.admins (
    user_id INTEGER PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
    admin_level INTEGER DEFAULT 1  -- For potential future use (different admin levels)
);

-- Create user_roles junction table
CREATE TABLE public.user_roles (
    user_id INTEGER REFERENCES public.users(id) ON DELETE CASCADE,
    role_id INTEGER REFERENCES public.roles(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, role_id)
);

-- Create profiles table for additional user information
CREATE TABLE public.profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES public.users(id) ON DELETE CASCADE,
    bio TEXT,
    avatar_url VARCHAR(255),
    social_links JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create password_reset_tokens table
CREATE TABLE public.password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES public.users(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used BOOLEAN DEFAULT FALSE
);

-- Insert default roles
INSERT INTO public.roles (name, description) VALUES
    ('admin', 'Administrator with full system access'),
    ('student', 'Regular student user');

-- Insert admin user (two-step process)
WITH new_user AS (
    INSERT INTO public.users (name, surname, email, password, is_active, user_type)
    VALUES ('Admin', 'User', 'admin@erasmustalk.com', 'admin123', true, 'admin')
    RETURNING id
)
INSERT INTO public.admins (user_id, admin_level)
SELECT id, 1 FROM new_user;

-- Assign admin role to admin user
INSERT INTO public.user_roles (user_id, role_id)
SELECT u.id, r.id
FROM public.users u, public.roles r
WHERE u.email = 'admin@erasmustalk.com' AND r.name = 'admin';

-- Create view for easier querying
CREATE OR REPLACE VIEW public.all_users AS
    SELECT 
        u.*,
        s.department,
        s.going_to,
        a.admin_level
    FROM public.users u
    LEFT JOIN public.students s ON u.id = s.user_id
    LEFT JOIN public.admins a ON u.id = a.user_id;
"""

try:
    print("Creating database engine...")
    engine = create_engine(db_connection_string, echo=True)
    
    print("Attempting to connect to database...")
    with engine.connect() as conn:
        print("Connected successfully. Creating tables...")
        
        # Split the SQL into individual statements and execute them
        statements = [stmt.strip() for stmt in create_tables_sql.split(';') if stmt.strip()]
        for i, statement in enumerate(statements, 1):
            print(f"Executing statement {i}/{len(statements)}...")
            try:
                conn.execute(text(statement))
                print(f"Statement {i} executed successfully")
            except Exception as stmt_error:
                print(f"Error executing statement {i}:")
                print(statement)
                print(f"Error: {str(stmt_error)}")
                raise
        
        print("Committing changes...")
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