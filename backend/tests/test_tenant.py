import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from app.core.tenant import get_current_tenant
from app.core.security import create_access_token


class TestGetCurrentTenant:
    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        return db

    @pytest.fixture
    def tenant_id(self):
        return "f64ac857-8ee0-487a-a527-7399aff8ad93"

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self, mock_db):
        with pytest.raises(HTTPException) as exc:
            await get_current_tenant(token="invalid_token", db=mock_db)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_tenant_not_found_returns_401(self, mock_db, tenant_id):
        token = create_access_token(tenant_id)
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc:
            await get_current_tenant(token=token, db=mock_db)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_tenant_returns_tenant(self, mock_db, tenant_id):
        token = create_access_token(tenant_id)
        mock_tenant = MagicMock()
        mock_tenant.id = tenant_id
        mock_tenant.is_active = True

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_tenant)
        mock_db.execute.return_value = mock_result

        result = await get_current_tenant(token=token, db=mock_db)
        assert result == mock_tenant
