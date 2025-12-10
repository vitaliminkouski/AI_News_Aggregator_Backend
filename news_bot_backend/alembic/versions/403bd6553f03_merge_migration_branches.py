"""merge migration branches

Revision ID: 403bd6553f03
Revises: e9897060a2cd, 7b9e6c079f27
Create Date: 2025-12-05 23:14:55.033481

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '403bd6553f03'
down_revision: Union[str, Sequence[str], None] = ('e9897060a2cd', '7b9e6c079f27')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
