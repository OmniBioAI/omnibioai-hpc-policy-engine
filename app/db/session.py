"""
OmniBioAI app.db.session.

Purpose:
    Defines DATABASE_URL, engine, SessionLocal and Base values for app.db.session.

Author:
    Manish Kumar <manish@omnibioai.org>
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import Config

DATABASE_URL = (
    f"mysql+pymysql://{Config.MYSQL_USER}:"
    f"{Config.MYSQL_PASSWORD}@"
    f"{Config.MYSQL_HOST}:{Config.MYSQL_PORT}/"
    f"{Config.MYSQL_DB}"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()