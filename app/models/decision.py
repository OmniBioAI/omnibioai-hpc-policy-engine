"""
OmniBioAI app.models.decision.

Purpose:
    Defines the Decision data model for app.models.decision.

Author:
    Manish Kumar <manish@omnibioai.org>
"""

from pydantic import BaseModel


class Decision(BaseModel):
    allow: bool
    reason: str

    remaining_cpu_hours: float = 0
    remaining_gpu_hours: float = 0