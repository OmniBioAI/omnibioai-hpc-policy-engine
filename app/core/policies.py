def validate_partition_access(roles: list, partition: str):

    if partition == "dgx-a100" and "dgx_access" not in roles:
        return False, "dgx partition denied"

    return True, "partition allowed"
