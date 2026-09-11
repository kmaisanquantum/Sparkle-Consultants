import hmac
import hashlib
import uuid
from typing import Dict, Any, Optional

from app.core.config import settings
from app.services.payments.base import PaymentProvider

class BSPPaymentProvider(PaymentProvider):
    """
    Bank South Pacific (BSP) Payment Provider Adapter.

    IMPORTANT ARCHITECTURAL DIRECTIVE:
    This adapter provides provider-independent abstractions for BSP payment gateway
    services (repayment collections and loan disbursements).
    Real BSP integration endpoints must use only official, approved BSP merchant services.
    Credentials must be loaded exclusively from environment variables / secrets settings.
    """

    def __init__(self):
        # Secrets loaded from Settings configuration (never hardcoded)
        self.merchant_id = getattr(settings, "bsp_merchant_id", "SPARKLE_BSP_MERCHANT_DEFAULT")
        self.webhook_secret = getattr(settings, "bsp_webhook_secret", "CHANGE_ME_BSP_WEBHOOK_SECRET")
        self.environment = getattr(settings, "bsp_environment", "sandbox")

    async def initiate_collection(
        self,
        amount: float,
        currency: str,
        customer_reference: str,
        idempotency_key: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        # TODO: BSP Real Integration — replace stub with official BSP Merchant Payment API endpoint
        # Real integration must connect via approved BSP web API / ISO20022 message specs.
        provider_ref = f"BSP-PAY-{uuid.uuid4().hex[:12].upper()}"
        return {
            "provider": "bsp",
            "provider_reference": provider_ref,
            "status": "successful",
            "amount": amount,
            "currency": currency or "PGK",
            "idempotency_key": idempotency_key,
            "redirect_url": f"https://bsp-pay-gateway.pg/pay/{provider_ref}" if self.environment == "sandbox" else None,
            "message": "BSP payment initiated successfully (Stubbed for approved BSP integration)"
        }

    async def initiate_disbursement(
        self,
        amount: float,
        currency: str,
        bank_account_hash: str,
        account_name: str,
        bsb_code: Optional[str],
        idempotency_key: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        # TODO: BSP Real Integration — replace stub with official BSP Bulk Transfer / Direct Credit API
        # Real integration must connect via approved BSP corporate banking file upload or direct API.
        provider_ref = f"BSP-DISB-{uuid.uuid4().hex[:12].upper()}"
        return {
            "provider": "bsp",
            "provider_reference": provider_ref,
            "status": "disbursed",
            "amount": amount,
            "currency": currency or "PGK",
            "idempotency_key": idempotency_key,
            "message": "BSP direct credit disbursement processed successfully (Stubbed for approved BSP integration)"
        }

    async def verify_webhook(
        self,
        payload: bytes,
        signature_header: str
    ) -> bool:
        # TODO: BSP Real Integration — verify HMAC SHA-256 webhook payload signature
        if not signature_header:
            return False
        expected_sig = hmac.new(
            self.webhook_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected_sig, signature_header)

    async def check_status(
        self,
        provider_reference: str
    ) -> Dict[str, Any]:
        # TODO: BSP Real Integration — poll official BSP transaction status query endpoint
        return {
            "provider": "bsp",
            "provider_reference": provider_reference,
            "status": "successful",
            "reconciled": True
        }
