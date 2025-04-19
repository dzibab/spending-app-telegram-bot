"""Baseline

Revision ID: 1
Revises: 620ba9b3eac6
Create Date: 2025-04-19 19:52:13.612308

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1"
down_revision: Union[str, None] = "620ba9b3eac6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
