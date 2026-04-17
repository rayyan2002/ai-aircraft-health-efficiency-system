# backend/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# 1. Define the database URL (SQLite looks in the local directory)
SQLALCHEMY_DATABASE_URL = "sqlite:///./aviation_data.db"

# 2. Create the SQLAlchemy Engine
# The 'check_same_thread' argument is strictly for SQLite in FastAPI
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 3. Create a SessionLocal class for database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. Create a Base class that all our models will inherit from
Base = declarative_base()

# 5. Dependency to get the DB session in FastAPI routes
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()