import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from app.models.interview import Interview
from app.models.interview_message import InterviewMessage
from app.models.interview_report import InterviewReport


class TestDeleteInterview:
    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_tenant(self):
        tenant = MagicMock()
        tenant.id = "tenant-uuid"
        return tenant

    @pytest.fixture
    def interview_id(self):
        return "interview-uuid"

    @pytest.mark.asyncio
    async def test_delete_interview_success(self, mock_db, mock_tenant, interview_id):
        from app.api.v1.interviews import delete_interview

        mock_interview = MagicMock()
        mock_interview.id = interview_id

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_interview)
        mock_db.execute.return_value = mock_result

        result = await delete_interview(interview_id, mock_tenant, mock_db)
        assert result == {"deleted": interview_id}

    @pytest.mark.asyncio
    async def test_delete_interview_not_found(self, mock_db, mock_tenant, interview_id):
        from app.api.v1.interviews import delete_interview

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=None)
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc:
            await delete_interview(interview_id, mock_tenant, mock_db)
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_interview_cascades_messages_and_report(self, mock_db, mock_tenant, interview_id):
        from app.api.v1.interviews import delete_interview

        mock_interview = MagicMock()
        mock_interview.id = interview_id

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=mock_interview)
        mock_db.execute.return_value = mock_result

        await delete_interview(interview_id, mock_tenant, mock_db)

        # Verify delete was called for messages, report, and interview
        assert mock_db.execute.call_count >= 4  # select + 3 deletes


class TestBatchDeleteInterviews:
    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def mock_tenant(self):
        tenant = MagicMock()
        tenant.id = "tenant-uuid"
        return tenant

    @pytest.mark.asyncio
    async def test_batch_delete_success(self, mock_db, mock_tenant):
        from app.api.v1.interviews import batch_delete_interviews
        from app.schemas.interview import BatchDeleteInterviews

        ids = ["id-1", "id-2"]
        data = BatchDeleteInterviews(ids=ids)

        # First call: select tenant-owned interview IDs
        tenant_result = AsyncMock()
        tenant_result.fetchall = MagicMock(return_value=[("id-1",), ("id-2",)])

        # Subsequent calls: delete operations need rowcount
        delete_result = AsyncMock()
        delete_result.rowcount = 2

        mock_db.execute.side_effect = [tenant_result, delete_result, delete_result, delete_result]

        result = await batch_delete_interviews(data, mock_tenant, mock_db)
        assert result["deleted"] == 2

    @pytest.mark.asyncio
    async def test_batch_delete_no_matching_tenant(self, mock_db, mock_tenant):
        from app.api.v1.interviews import batch_delete_interviews
        from app.schemas.interview import BatchDeleteInterviews

        data = BatchDeleteInterviews(ids=["other-tenant-id"])

        tenant_result = AsyncMock()
        tenant_result.fetchall = MagicMock(return_value=[])
        mock_db.execute.return_value = tenant_result

        result = await batch_delete_interviews(data, mock_tenant, mock_db)
        assert result == {"deleted": 0}

    @pytest.mark.asyncio
    async def test_batch_delete_empty_ids_rejected(self):
        from app.schemas.interview import BatchDeleteInterviews
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            BatchDeleteInterviews(ids=[])
