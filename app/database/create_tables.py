from app.database.connection import engine
from app.models.core import Base

def create_all_tables():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    create_all_tables()
    print("TABLES_CREATED")
