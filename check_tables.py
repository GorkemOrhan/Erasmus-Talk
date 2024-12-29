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
        expected_tables = {'students', 'profiles', 'password_reset_tokens'}
        existing_tables = {table[0] for table in tables}
        missing_tables = expected_tables - existing_tables
        
        if missing_tables:
            print("\nMissing tables:")
            for table in missing_tables:
                print(f"- {table}")
        else:
            print("\nAll required tables exist in public schema!")
            
except Exception as e:
    print(f"Error checking tables: {str(e)}") 