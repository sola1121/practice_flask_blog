"""empty message

Revision ID: 4444004e4702
Revises: 08d6040bc09b
Create Date: 2019-01-27 16:59:25.468865

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4444004e4702'
down_revision = '08d6040bc09b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('posts', sa.Column('body_html', sa.Text(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('posts', 'body_html')
    # ### end Alembic commands ###
