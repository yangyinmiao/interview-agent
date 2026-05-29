"""add_jd_title_company

Revision ID: add_jd_title_company
Revises: 1da75b400930
Create Date: 2026-05-28 00:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'add_jd_title_company'
down_revision: Union[str, None] = '1da75b400930'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('jds', sa.Column('title', sa.String(200), nullable=True))
    op.add_column('jds', sa.Column('company', sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column('jds', 'company')
    op.drop_column('jds', 'title')
