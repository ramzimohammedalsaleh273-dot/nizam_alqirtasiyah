from pathlib import Path
from sqlalchemy import create_engine, text

BASE_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BASE_DIR / "database"
DB_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DB_DIR / "nizam_alqirtasiyah.db"
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

def initialize_database():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS system_info (
                id INTEGER PRIMARY KEY,
                system_name TEXT NOT NULL,
                version TEXT NOT NULL
            )
        """))

        conn.execute(text("""
            INSERT OR IGNORE INTO system_info
            (id, system_name, version)
            VALUES (1, 'نظام القرطاسية', '1.0.0')
        """))

if __name__ == "__main__":
    initialize_database()
    print("DATABASE_CREATED")
    print(DB_PATH)
