
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
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        # Fix protocol issues for SQLAlchemy
        if env_url.startswith("postgres://"):
            env_url = env_url.replace("postgres://", "postgresql://", 1)
        elif env_url.startswith("mysql://") and not env_url.startswith("mysql+"):
            env_url = env_url.replace("mysql://", "mysql+pymysql://", 1)
        return env_url
    
    # 2. Check local config file (Priority 2)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                config = json.load(f)
                config_url = config.get("DATABASE_URL")
                if config_url:
                    # Fix protocol issues
                    if config_url.startswith("postgres://"):
                        config_url = config_url.replace("postgres://", "postgresql://", 1)
                    elif config_url.startswith("mysql://") and not config_url.startswith("mysql+"):
                        config_url = config_url.replace("mysql://", "mysql+pymysql://", 1)
                    return config_url
        except Exception:
            pass
            
    # 3. Fallback to SQLite (Priority 3)
    return f"sqlite:///{DEFAULT_SQLITE_PATH}"

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
