"""
OmniBioAI app.core.quota.

Purpose:
    Defines evaluate_quota for app.core.quota.

Author:
    Manish Kumar <manish@omnibioai.org>
"""

from app.core.config import Config


def evaluate_quota(
    current_cpu: float,
    current_gpu: float,
    request_cpu: float,
    request_gpu: float,
):

    remaining_cpu = Config.DEFAULT_CPU_HOURS - current_cpu
    remaining_gpu = Config.DEFAULT_GPU_HOURS - current_gpu

    if request_cpu > remaining_cpu:
        return False, "cpu quota exceeded", remaining_cpu, remaining_gpu

    if request_gpu > remaining_gpu:
        return False, "gpu quota exceeded", remaining_cpu, remaining_gpu

    return True, "quota ok", remaining_cpu, remaining_gpu