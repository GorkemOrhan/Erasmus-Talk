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

-- Create students table
DROP TABLE IF EXISTS public.password_reset_tokens;
DROP TABLE IF EXISTS public.profiles;
DROP TABLE IF EXISTS public.students;

CREATE TABLE public.students (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    surname VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    department VARCHAR(100) NOT NULL,
    going_to VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT FALSE,
    activation_token VARCHAR(255)
);

-- Create profiles table for additional user information
CREATE TABLE public.profiles (
    id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES public.students(id),
    bio TEXT,
    avatar_url VARCHAR(255),
    social_links JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create password_reset_tokens table
CREATE TABLE public.password_reset_tokens (
    id SERIAL PRIMARY KEY,
    student_id INTEGER REFERENCES public.students(id),
    token VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used BOOLEAN DEFAULT FALSE
);
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