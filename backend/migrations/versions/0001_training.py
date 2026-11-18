import sqlalchemy as sa
from alembic import op

revision = "0001_training"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "training_sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("token_digest", sa.String(64), nullable=False),
        sa.Column("phase", sa.String(2), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("created_at", sa.Integer, nullable=False),
        sa.Column("final_request", sa.JSON(none_as_null=True)),
        sa.Column("report", sa.JSON(none_as_null=True)),
    )
    op.create_index(
        "ix_training_sessions_created_at", "training_sessions", ["created_at"]
    )
    op.create_table(
        "training_turns",
        sa.Column("seq", sa.Integer, primary_key=True),
        sa.Column(
            "session_id",
            sa.String(36),
            sa.ForeignKey("training_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("client_id", sa.String(36), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False, unique=True),
        sa.Column("reply_id", sa.String(36), nullable=False, unique=True),
        sa.Column("role_id", sa.String(12), nullable=False),
        sa.Column("user_text", sa.Text, nullable=False),
        sa.Column("reply", sa.Text, nullable=False),
        sa.Column("facts", sa.JSON, nullable=False),
        sa.Column("presented", sa.Boolean, nullable=False),
        sa.Column("created_at", sa.Integer, nullable=False),
        sa.UniqueConstraint("session_id", "client_id", name="uq_turn_request"),
    )
    op.create_index("ix_training_turns_session_id", "training_turns", ["session_id"])


def downgrade():
    op.drop_table("training_turns")
    op.drop_table("training_sessions")
