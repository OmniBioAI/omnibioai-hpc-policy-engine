from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db

from app.models.quota import QuotaCheck
from app.services.usage_service import UsageService
from app.services.quota_service import QuotaService

router = APIRouter(prefix="/quota", tags=["quota"])


@router.post("/check")
async def check_quota(
    request: QuotaCheck,
    db: Session = Depends(get_db),
):

    usage = UsageService.get_or_create_user_usage(
        db,
        request.user_id,
    )

    decision = QuotaService.evaluate(
        usage=usage,
        request=request,
        # PR12: was hardcoded to ["gpu_user"], granting every caller GPU
        # access regardless of their real roles -- now scoped to whatever
        # the caller actually supplied (defaults to [] -- no roles).
        roles=request.roles,
    )

    return decision