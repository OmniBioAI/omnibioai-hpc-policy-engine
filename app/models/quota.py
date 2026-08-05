from pydantic import BaseModel


class QuotaCheck(BaseModel):
    user_id: str

    cpu_hours: float = 0
    gpu_hours: float = 0

    gpus: int = 0
    # PR12: QuotaService.evaluate already reads request.partition (used by
    # validate_partition_access) -- this field didn't exist on the model at
    # all, a pre-existing gap documented in tests/test_routes_quota.py's
    # module docstring, worked around there by mocking QuotaService.evaluate
    # entirely rather than exercising the real path.
    partition: str = "cpu"
    # PR12: caller-supplied roles -- /quota/check previously hardcoded
    # roles=["gpu_user"] for every request regardless of who actually
    # called it (see routes_quota.py), meaning GPU/DGX quota checks were
    # never actually scoped to the real requester.
    roles: list[str] = []