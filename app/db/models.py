"""
OmniBioAI app.db.models.

Purpose:
    Defines the UsageRecord data model for app.db.models.

Author:
    Manish Kumar <manish@omnibioai.org>
"""

from sqlalchemy import Column, Float, Integer, String

from app.db.session import Base


class UsageRecord(Base):
    __tablename__ = "usage_records"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(String(128), index=True)

    cpu_hours = Column(Float, default=0)
    gpu_hours = Column(Float, default=0)

    jobs_running = Column(Integer, default=0)