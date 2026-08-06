from fastapi import APIRouter
from app.models.job import JobRequest
from app.core.gpu import validate_gpu_access
from app.core.policies import validate_partition_access

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/evaluate")
async def evaluate_job(request: JobRequest):
    # PR12: this previously always returned "job approved" regardless of
    # gpus/partition/roles -- validate_gpu_access/validate_partition_access
    # already existed (and are already exercised via QuotaService for
    # /quota/check) but were never wired up here. Same checks, same order
    # QuotaService.evaluate uses.
    ok, reason = validate_gpu_access(request.roles, request.gpus)
    if not ok:
        return {"allow": False, "reason": reason, "partition": request.partition}

    ok, reason = validate_partition_access(request.roles, request.partition)
    if not ok:
        return {"allow": False, "reason": reason, "partition": request.partition}

    return {
        "allow": True,
        "reason": "job approved",
        "partition": request.partition,
    }