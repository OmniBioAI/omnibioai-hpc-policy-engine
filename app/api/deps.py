"""
OmniBioAI app.api.deps.

Purpose:
    Defines get_db for app.api.deps.

Author:
    Manish Kumar <manish@omnibioai.org>
"""

from app.db.session import SessionLocal


def get_db():

    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()