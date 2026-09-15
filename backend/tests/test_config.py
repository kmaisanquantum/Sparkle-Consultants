import os
import pytest

from app.core.config import Settings


def test_database_url_normalization():
    s1 = Settings(database_url="postgres://postgres:pw@host:5432/postgres")
    assert s1.database_url == "postgresql+asyncpg://postgres:pw@host:5432/postgres"

    s2 = Settings(database_url="postgresql://postgres:pw@host:5432/postgres")
    assert s2.database_url == "postgresql+asyncpg://postgres:pw@host:5432/postgres"

    s3 = Settings(database_url="postgresql+asyncpg://postgres:pw@host:5432/postgres")
    assert s3.database_url == "postgresql+asyncpg://postgres:pw@host:5432/postgres"
