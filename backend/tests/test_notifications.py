import pytest
from app.services.notification_service import NotificationService, SMSGatewayProvider


def test_sms_gateway_stub():
    sms = SMSGatewayProvider()
    res = sms.send_sms("+67571234567", "Test alert message")
    assert res is True
