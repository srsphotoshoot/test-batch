
import os
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool

# Default path for SQLite fallback
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SQLITE_PATH = os.path.join(BASE_DIR, "batches.db")
CONFIG_PATH = os.path.join(BASE_DIR, "db_config.json")

Base = declarative_base()

def get_db_url():
    # 1. Check environment variable (Priority 1)
    url = os.getenv("DATABASE_URL")
    
    # 2. Check local config file (Priority 2)
    if not url and os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                config = json.load(f)
                url = config.get("DATABASE_URL")
        except Exception:
            pass
            
    # 3. Fallback to SQLite (Priority 3)
    if not url:
        return f"sqlite:///{DEFAULT_SQLITE_PATH}"

    # Robust Protocol Fixing for SQLAlchemy 2.0+
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://") and "+psycopg2" not in url:
         url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    elif url.startswith("mysql://") and not url.startswith("mysql+"):
        url = url.replace("mysql://", "mysql+pymysql://", 1)

    # Automatic SSL enforcement for remote Postgres (Supabase/Railway)
    if "postgresql" in url and "localhost" not in url and "127.0.0.1" not in url:
        if "sslmode=" not in url:
            separator = "&" if "?" in url else "?"
            url += f"{separator}sslmode=require"

    return url

def create_db_engine():
    url = get_db_url()
    
    # Special args for SQLite
    if url.startswith("sqlite"):
        return create_engine(
            url, 
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
    
    # Standard args for other DBs
    return create_engine(url, pool_pre_ping=True)

# Global engine and session factory
engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def reset_engine():
    """Call this when DB config changes to re-initialize the engine"""
    global engine, SessionLocal
    engine.dispose()
    engine = create_db_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
