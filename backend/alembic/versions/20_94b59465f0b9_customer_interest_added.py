"""customer interest added

Revision ID: 94b59465f0b9
Revises: 9b1081ac4f00
Create Date: 2025-04-09 20:21:34.026872

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '94b59465f0b9'
down_revision: Union[str, None] = '9b1081ac4f00'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('transcribe_ai', sa.Column('customer_interest', sa.JSON(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('transcribe_ai', 'customer_interest')
    # ### end Alembic commands ###
