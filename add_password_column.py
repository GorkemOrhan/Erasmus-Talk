from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

env = os.getenv('FLASK_ENV', 'development')
dotenv_path = f'.env.{env}'
load_dotenv(dotenv_path)

db_connection_string = os.environ["DB_CONNECTION_STR"]
db_connection_string = db_connection_string.strip('"').strip("'")

engine = create_engine(db_connection_string)

with engine.connect() as conn:
    conn.execute(text("ALTER TABLE students ADD COLUMN IF NOT EXISTS password VARCHAR(255);"))
    conn.commit()
    print("Password column added successfully!") 