from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
import psycopg2
import os

# Base class for all ORM models
Base = declarative_base()

# Engine & session will be initialized later (Step 2)
engine = None
SessionLocal = scoped_session(sessionmaker())


def init_db(database_url: str):
    """
    Initialize SQLAlchemy engine and session factory.
    Called once at app startup (later).
    """
    global engine
    engine = create_engine(
    database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    future=True,
)
    SessionLocal.configure(bind=engine)

def get_pg_connection():
    required_vars = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]
    print("DB_USER:", os.getenv("DB_USER"))
    print("DB_PASSWORD:", os.getenv("DB_PASSWORD"))
    for var in required_vars:
        if not os.environ.get(var):
            raise RuntimeError(f"Missing required environment variable: {var}")

    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        database=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        port=os.environ.get("DB_PORT", "5432"),
    )