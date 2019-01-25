"""empty message

Revision ID: 306548df23ed
Revises: 63d30a36ddf9
Create Date: 2019-01-25 17:07:02.654847

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '306548df23ed'
down_revision = '63d30a36ddf9'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('avatar_hash', sa.String(length=32), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'avatar_hash')
    # ### end Alembic commands ###
