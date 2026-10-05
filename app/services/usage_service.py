"""
OmniBioAI app.services.usage_service.

Purpose:
    Defines UsageService with get_or_create_user_usage methods for app.services.usage_service.

Author:
    Manish Kumar <manish@omnibioai.org>
"""

from sqlalchemy.orm import Session

from app.db.models import UsageRecord


class UsageService:

    @staticmethod
    def get_or_create_user_usage(db: Session, user_id: str):

        usage = (
            db.query(UsageRecord)
            .filter(UsageRecord.user_id == user_id)
            .first()
        )

        if usage:
            return usage

        usage = UsageRecord(
            user_id=user_id,
            cpu_hours=0,
            gpu_hours=0,
            jobs_running=0,
        )

        db.add(usage)
        db.commit()
        db.refresh(usage)

        return usage