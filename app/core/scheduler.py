"""
OmniBioAI app.core.scheduler.

Purpose:
    Defines SchedulerAdapter with get_cluster_load methods for app.core.scheduler.

Author:
    Manish Kumar <manish@omnibioai.org>
"""

class SchedulerAdapter:

    async def get_cluster_load(self):

        return {
            "cpu_load": 0.45,
            "gpu_load": 0.60,
            "running_jobs": 21,
        }