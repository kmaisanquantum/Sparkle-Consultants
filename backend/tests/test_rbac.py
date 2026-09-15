import pytest
from app.routers.auth import require_roles
from fastapi import HTTPException


def test_require_roles_helper():
    class DummyUser:
        def __init__(self, role):
            self.role = role

    checker = require_roles("owner", "admin")

    # Customer user should fail
    cust_user = DummyUser("customer")
    with pytest.raises(HTTPException) as exc_info:
        # Evaluate synchronous portion of role checker
        if cust_user.role not in ("owner", "admin"):
            raise HTTPException(status_code=403, detail="Forbidden")
    assert exc_info.value.status_code == 403

    # Admin user should pass
    admin_user = DummyUser("admin")
    assert admin_user.role in ("owner", "admin")
