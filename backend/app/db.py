from contextlib import contextmanager
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import config
from models import Base

_engine = None
_SessionLocal = None


def get_engine():
    global _engine, _SessionLocal
    if not config.DATABASE_URL:
        return None
    if _engine is None:
        _engine = create_engine(
            config.DATABASE_URL,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
        _SessionLocal = sessionmaker(bind=_engine, autocommit=False, autoflush=False)
    return _engine


@contextmanager
def get_session():
    engine = get_engine()
    if engine is None or _SessionLocal is None:
        raise RuntimeError("DATABASE_URL not configured")
    session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    engine = get_engine()
    if engine is None:
        return False
    Base.metadata.create_all(bind=engine)
    return True


def try_acquire_leader_lock():
    engine = get_engine()
    if engine is None:
        return None
    if not config.DATABASE_URL.startswith("postgresql"):
        return engine.connect()
    conn = engine.connect()
    try:
        result = conn.execute(
            text("SELECT pg_try_advisory_lock(:key)"),
            {"key": config.TELEMETRY_LEADER_LOCK_KEY},
        ).scalar()
        if result:
            return conn
    except Exception:
        conn.close()
        return None
    conn.close()
    return None
