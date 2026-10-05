"""
OmniBioAI app.core.policies.

Purpose:
    Defines validate_partition_access for app.core.policies.

Author:
    Manish Kumar <manish@omnibioai.org>
"""

def validate_partition_access(roles: list, partition: str):

    if partition == "dgx-a100" and "dgx_access" not in roles:
        return False, "dgx partition denied"

    return True, "partition allowed"
