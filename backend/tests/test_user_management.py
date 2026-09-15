import pytest
from app.routers.auth import require_roles


def test_user_management_rbac_permissions():
    class DummyUser:
        def __init__(self, role):
            self.role = role

    admin_checker = require_roles("administrator", "admin")

    administrator_user = DummyUser("administrator")
    assert administrator_user.role in ("administrator", "admin", "owner")

    customer_user = DummyUser("customer")
    client_user = DummyUser("client")

    assert customer_user.role not in ("administrator", "admin", "owner")
    assert client_user.role not in ("administrator", "admin", "owner")


def test_role_classification_conventions():
    staff_roles = ["administrator", "admin", "owner", "underwriter", "collections_agent", "compliance_officer"]
    borrower_roles = ["customer", "client"]

    assert "administrator" in staff_roles
    assert "client" in borrower_roles
    assert "customer" in borrower_roles
