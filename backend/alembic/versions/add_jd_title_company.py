"""add_jd_title_company

Revision ID: add_jd_title_company
Revises: 1da75b400930
Create Date: 2026-05-28 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op

revision: str = 'add_jd_title_company'
down_revision: Union[str, None] = '1da75b400930'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Some early development databases received these columns before the
    # Alembic revision was recorded. Keep the revision safe for both those
    # databases and clean installations.
    op.execute("ALTER TABLE jds ADD COLUMN IF NOT EXISTS title VARCHAR(200)")
    op.execute("ALTER TABLE jds ADD COLUMN IF NOT EXISTS company VARCHAR(200)")


def downgrade() -> None:
    op.drop_column('jds', 'company')
    op.drop_column('jds', 'title')
