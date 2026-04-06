from sqlalchemy import create_engine, text

DATABASE_URL = "=mysql+aiomysql://root:Ram#5408@localhost/financedb"

try:
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print("✅ DB working:", result.scalar())

except Exception as e:
    print("❌ DB error:", e)