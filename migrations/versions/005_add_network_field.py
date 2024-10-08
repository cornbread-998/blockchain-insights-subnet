"""Add network field

Revision ID: 005
Revises: 004
Create Date: 2024-09-04 20:43:03.664372

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DELETE FROM validation_prompt")
    op.add_column('validation_prompt', sa.Column('network', sa.String(), nullable=False))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('validation_prompt', 'network')
    # ### end Alembic commands ###
