from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
import traceback

# Load environment variables
env = os.getenv('FLASK_ENV', 'development')
dotenv_path = f'.env.{env}'
load_dotenv(dotenv_path)

db_connection_string = os.environ["DB_CONNECTION_STR"]
db_connection_string = db_connection_string.strip('"').strip("'")

engine = create_engine(db_connection_string)

# Create tables
sql_statements = [
    # Enable pgcrypto extension
    "CREATE EXTENSION IF NOT EXISTS pgcrypto",
    
    # Create users table with updated schema
    """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        email VARCHAR(120) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        first_name VARCHAR(50),
        last_name VARCHAR(50),
        is_active BOOLEAN DEFAULT FALSE,
        is_admin BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
    )
    """,
    
    # Create activation tokens table
    """
    CREATE TABLE IF NOT EXISTS activation_tokens (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        token VARCHAR(100) UNIQUE NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
        used BOOLEAN DEFAULT FALSE
    )
    """,
    
    # Create password reset tokens table
    """
    CREATE TABLE IF NOT EXISTS password_reset_tokens (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        token VARCHAR(100) UNIQUE NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
        used BOOLEAN DEFAULT FALSE
    )
    """
]

try:
    with engine.connect() as conn:
        # Execute all statements
        for statement in sql_statements:
            conn.execute(text(statement))
        conn.commit()
        print("Database tables created successfully!")
except Exception as e:
    print(f"Error: {str(e)}")
    raise 