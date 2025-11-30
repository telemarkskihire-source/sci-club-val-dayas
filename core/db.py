
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Per sviluppo usiamo un semplice SQLite locale
DATABASE_URL = "sqlite:///sci_club_val_dayas.db"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)

Base = declarative_base()
