"""
OmniBioAI app.services.quota_service.

Purpose:
    Defines QuotaService with evaluate methods for app.services.quota_service.

Author:
    Manish Kumar <manish@omnibioai.org>
"""

from app.core.gpu import validate_gpu_access
from app.core.policies import validate_partition_access
from app.core.quota import evaluate_quota
from app.models.decision import Decision


class QuotaService:

    @staticmethod
    def evaluate(
        usage,
        request,
        roles: list,
    ) -> Decision:

        ok, reason = validate_gpu_access(
            roles,
            request.gpus,
        )

        if not ok:
            return Decision(
                allow=False,
                reason=reason,
            )

        ok, reason = validate_partition_access(
            roles,
            request.partition,
        )

        if not ok:
            return Decision(
                allow=False,
                reason=reason,
            )

        ok, reason, rem_cpu, rem_gpu = evaluate_quota(
            usage.cpu_hours,
            usage.gpu_hours,
            request.cpu_hours,
            request.gpu_hours,
        )

        return Decision(
            allow=ok,
            reason=reason,
            remaining_cpu_hours=rem_cpu,
            remaining_gpu_hours=rem_gpu,
        )