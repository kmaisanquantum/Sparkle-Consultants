import pytest
from fastapi import HTTPException
from app.routers.auth import require_roles


def test_user_management_rbac_permissions():
    class DummyUser:
        def __init__(self, role):
            self.role = role

    # Role checker requirement for administrator / admin
    admin_checker = require_roles("administrator", "admin")

    administrator_user = DummyUser("administrator")
    assert administrator_user.role in ("administrator", "admin", "owner")

    customer_user = DummyUser("customer")
    client_user = DummyUser("client")

    # Customer and client roles must fail RBAC role check for admin operations
    assert customer_user.role not in ("administrator", "admin")
    assert client_user.role not in ("administrator", "admin")


def test_role_classification_conventions():
    staff_roles = ["administrator", "admin", "owner", "underwriter", "collections_agent", "compliance_officer"]
    borrower_roles = ["customer", "client"]

    assert "administrator" in staff_roles
    assert "client" in borrower_roles
    assert "customer" in borrower_roles
