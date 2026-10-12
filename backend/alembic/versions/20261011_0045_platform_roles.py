"""Migrate users to explicit platform roles.

Organization membership roles remain unchanged and continue to represent
workspace permissions. Legacy ``owner`` and ``admin`` values are preserved as
platform ``admin`` so legitimate administrative access is not silently
revoked. Legacy ``member`` values become platform ``user``. No
``super_admin`` is created by migration.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0045_platform_roles"
down_revision: Union[str, tuple[str, str], None] = (
    "0044_self_hosted_auth",
    "0049_leads_conversation_idx",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE user_role_new AS ENUM ('super_admin', 'admin', 'manager', 'user')"
    )
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE user_role_new USING "
        "CASE role::text WHEN 'owner' THEN 'admin' "
        "WHEN 'admin' THEN 'admin' ELSE 'user' END::user_role_new"
    )
    op.execute("DROP TYPE user_role")
    op.execute("ALTER TYPE user_role_new RENAME TO user_role")
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'user'")
    op.execute("ALTER TABLE users ALTER COLUMN role SET NOT NULL")


def downgrade() -> None:
    op.execute("CREATE TYPE user_role_old AS ENUM ('owner', 'admin', 'member')")
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT")
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE user_role_old USING "
        "CASE role::text WHEN 'super_admin' THEN 'admin' WHEN 'admin' THEN 'admin' "
        "WHEN 'manager' THEN 'member' ELSE 'member' END::user_role_old"
    )
    op.execute("DROP TYPE user_role")
    op.execute("ALTER TYPE user_role_old RENAME TO user_role")
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'owner'")
    op.execute("ALTER TABLE users ALTER COLUMN role SET NOT NULL")
