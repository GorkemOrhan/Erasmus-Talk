from sqlalchemy import create_engine,text
import os

db_connection_string = os.environ["DB_CONNECTION_STR"]
db_connection_string = db_connection_string.strip('"').strip("'")

engine = create_engine(db_connection_string)

def load_students_from_db():
    with engine.connect() as conn:
        result = conn.execute(text("select * from students"))
        students = []
        for row in result.all():
            students.append(dict(row._mapping))
        return students
