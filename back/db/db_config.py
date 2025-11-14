from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

DATABASE_URL = os.environ.get("DATABASE_URL") or (
    f"postgresql://{os.environ.get('DB_USER','emg_user')}:"
    f"{os.environ.get('DB_PASSWORD','emg')}@"
    f"{os.environ.get('DB_HOST','db')}:"
    f"{os.environ.get('DB_PORT','5432')}/"
    f"{os.environ.get('DB_NAME','projetoemg')}"
)

# Engine e session factory
engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

# Base declarativa para seus modelos
Base = declarative_base()
