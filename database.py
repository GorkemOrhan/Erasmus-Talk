from sqlalchemy import create_engine, text

engine = create_engine('REDACTED')

with engine.connect() as conn:
    result = conn.execute(text("select * from students"))

    result_dicts = []
    for row in result.all():
        result_dicts.append(dict(row._mapping))
    print(result_dicts)