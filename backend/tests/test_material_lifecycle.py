from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.materials.lifecycle import PreparationMaterialLifecycle


@pytest.mark.asyncio
async def test_delete_removes_vectors_object_and_chunk_rows():
    db = AsyncMock()
    result = MagicMock()
    result.scalars.return_value.all.return_value = [
        SimpleNamespace(qdrant_point_id="f183fe0b-216a-457d-b36e-f0d44fe11b74")
    ]
    db.execute.side_effect = [result, MagicMock()]
    qdrant = MagicMock()
    minio = MagicMock()

    await PreparationMaterialLifecycle(db, qdrant=qdrant, minio=minio).delete(
        tenant_id="f64ac857-8ee0-487a-a527-7399aff8ad93",
        source_type="resume",
        source_id="f183fe0b-216a-457d-b36e-f0d44fe11b74",
        object_name="tenant/resumes/cv.pdf",
    )

    qdrant.delete.assert_called_once()
    minio.remove_object.assert_called_once()
    assert db.execute.await_count == 2
