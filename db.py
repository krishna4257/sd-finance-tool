from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session

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