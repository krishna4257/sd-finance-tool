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
        future=True,
    )
    SessionLocal.configure(bind=engine)

def get_pg_connection():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_NAME"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        port=os.environ.get("DB_PORT", "5432")
    )