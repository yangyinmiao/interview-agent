"""Persist interview runtime state and answer idempotency.

Revision ID: add_interview_runtime_state
Revises: add_jd_title_company
"""

from typing import Sequence, Union

from alembic import op


revision: str = "add_interview_runtime_state"
down_revision: Union[str, None] = "add_jd_title_company"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Reconcile legacy development databases where context_cache and
    # follow_up_depth were added before their revision existed.
    op.execute(
        "ALTER TABLE interviews ADD COLUMN IF NOT EXISTS max_rounds INTEGER DEFAULT 10"
    )
    op.execute(
        "ALTER TABLE interviews ADD COLUMN IF NOT EXISTS context_cache JSONB"
    )
    op.execute(
        "ALTER TABLE interviews ADD COLUMN IF NOT EXISTS follow_up_depth INTEGER DEFAULT 0"
    )
    op.execute("UPDATE interviews SET max_rounds = 10 WHERE max_rounds IS NULL")
    op.execute("UPDATE interviews SET follow_up_depth = 0 WHERE follow_up_depth IS NULL")
    op.execute("ALTER TABLE interviews ALTER COLUMN max_rounds SET DEFAULT 10")
    op.execute("ALTER TABLE interviews ALTER COLUMN max_rounds SET NOT NULL")
    op.execute("ALTER TABLE interviews ALTER COLUMN follow_up_depth SET DEFAULT 0")
    op.execute("ALTER TABLE interviews ALTER COLUMN follow_up_depth SET NOT NULL")
    op.execute(
        "ALTER TABLE interview_messages ADD COLUMN IF NOT EXISTS request_id VARCHAR(64)"
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_interview_message_request'
                  AND conrelid = 'interview_messages'::regclass
            ) THEN
                ALTER TABLE interview_messages
                ADD CONSTRAINT uq_interview_message_request
                UNIQUE (interview_id, request_id);
            END IF;
        END $$
        """
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_interview_message_request", "interview_messages", type_="unique"
    )
    op.drop_column("interview_messages", "request_id")
    op.drop_column("interviews", "follow_up_depth")
    op.drop_column("interviews", "context_cache")
    op.drop_column("interviews", "max_rounds")
