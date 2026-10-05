"""
OmniBioAI app.services.scheduler_service.

Purpose:
    Defines SchedulerService with cluster_status methods for app.services.scheduler_service.

Author:
    Manish Kumar <manish@omnibioai.org>
"""

from app.core.scheduler import SchedulerAdapter


class SchedulerService:

    def __init__(self):
        self.scheduler = SchedulerAdapter()

    async def cluster_status(self):
        return await self.scheduler.get_cluster_load()