from pydantic import BaseModel
from typing import Optional


class JobRequest(BaseModel):
    user_id: str

    cpu_hours: float = 0
    gpu_hours: float = 0

    gpus: int = 0
    memory_gb: int = 0

    partition: str = "cpu"

    # PR12: caller-supplied roles, used by /jobs/evaluate to actually run
    # the existing (previously unused) validate_gpu_access/
    # validate_partition_access checks instead of the prior unconditional
    # "job approved" stub. Defaults to [] so an existing caller that
    # doesn't supply roles gets the same (permissive, no-gpu/no-dgx-
    # partition) outcome those checks already give an empty roles list.
    roles: list[str] = []
    org_id: Optional[str] = None