import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.crypto import hash_password, verify_password
from app.core.migration import self_heal_schema


@pytest.mark.asyncio
async def test_password_hash_and_verify_roundtrip():
    password = "secret_password_123"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False


@pytest.mark.asyncio
async def test_self_heal_schema_executes_ddl():
    mock_conn = AsyncMock()
    mock_engine = MagicMock()
    mock_engine.dialect.name = "postgresql"
    mock_engine.begin.return_value.__aenter__.return_value = mock_conn

    await self_heal_schema(mock_engine)

    # Verify conn.execute was called multiple times for ALTER TABLE ... ADD COLUMN IF NOT EXISTS
    assert mock_conn.execute.call_count >= 15
    calls = mock_conn.execute.call_args_list
    first_query = str(calls[0][0][0])
    assert "ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_enabled" in first_query
