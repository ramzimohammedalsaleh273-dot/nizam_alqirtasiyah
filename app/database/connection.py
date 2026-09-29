
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import DATABASE_PATH

DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

def create_database_engine(database_path=None):
    path = database_path or DATABASE_PATH
    url = f"sqlite:///{path}"
    return create_engine(
        url,
        future=True,
        connect_args={"check_same_thread": False},
    )

engine = create_database_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)

def get_session():
    return SessionLocal()

def get_session_factory(database_path=None):
    test_engine = create_database_engine(database_path)
    return sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
        future=True,
    )

def database_health():
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA integrity_check")).scalar()
        foreign_keys = conn.execute(text("PRAGMA foreign_key_check")).fetchall()

    return {
        "integrity": result,
        "foreign_key_errors": len(foreign_keys),
        "healthy": result == "ok" and len(foreign_keys) == 0,
    }
