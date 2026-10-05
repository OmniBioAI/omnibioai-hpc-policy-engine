"""
OmniBioAI app.core.config.

Purpose:
    Defines the Config class for app.core.config.

Author:
    Manish Kumar <manish@omnibioai.org>
"""

import os


class Config:
    APP_NAME = "OmniBioAI HPC Policy Engine"

    MYSQL_HOST = os.getenv("MYSQL_HOST", "mysql")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_DB = os.getenv("MYSQL_DB", "omnibioai_hpc")
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root")

    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")

    DEFAULT_CPU_HOURS = int(os.getenv("DEFAULT_CPU_HOURS", "120"))
    DEFAULT_GPU_HOURS = int(os.getenv("DEFAULT_GPU_HOURS", "24"))

    MAX_CONCURRENT_JOBS = int(os.getenv("MAX_CONCURRENT_JOBS", "5"))