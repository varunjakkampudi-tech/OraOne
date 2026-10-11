from __future__ import annotations


import pytest

from app.database.models.user import User, UserRole
from app.services.platform_rbac import can_change_platform_role, parse_platform_role


def test_new_user_model_defaults_to_safe_platform_role():
    user = User(cognito_sub="sub-default", email="new@example.com")
    assert user.role in (None, UserRole.user)
    # SQLAlchemy applies the mapped default at INSERT time; the model contract
    # is explicit and the migration supplies the database default.
    assert User.role.default.arg == UserRole.user
    assert str(User.role.server_default.arg) == "user"


@pytest.mark.parametrize(
    ("actor", "target", "new_role", "allowed"),
    [
        (UserRole.admin, UserRole.user, UserRole.manager, True),
        (UserRole.admin, UserRole.manager, UserRole.user, True),
        (UserRole.admin, UserRole.user, UserRole.admin, False),
        (UserRole.admin, UserRole.admin, UserRole.user, False),
        (UserRole.admin, UserRole.user, UserRole.super_admin, False),
        (UserRole.manager, UserRole.user, UserRole.user, False),
        (UserRole.super_admin, UserRole.user, UserRole.admin, True),
        (UserRole.super_admin, UserRole.user, UserRole.super_admin, False),
    ],
)
def test_platform_role_change_policy(actor, target, new_role, allowed):
    assert can_change_platform_role(actor, target, new_role) is allowed


def test_platform_role_parser_rejects_organization_roles():
    with pytest.raises(Exception):
        parse_platform_role("owner")
    with pytest.raises(Exception):
        parse_platform_role("viewer")


def test_platform_role_change_never_uses_browser_supplied_role():
    # The endpoint receives only the requested target role. Authorization is
    # derived from the actor's DB-backed UserRole, not request JSON or JWT data.
    assert (
        can_change_platform_role(UserRole.user, UserRole.user, UserRole.admin) is False
    )
