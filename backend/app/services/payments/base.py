from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class PaymentProvider(ABC):
    @abstractmethod
    async def initiate_collection(
        self,
        amount: float,
        currency: str,
        customer_reference: str,
        idempotency_key: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Initiates a payment collection from a customer (e.g. via BSP online or API gateway)."""
        pass

    @abstractmethod
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
        """Initiates a loan disbursement to a borrower's bank account."""
        pass

    @abstractmethod
    async def verify_webhook(
        self,
        payload: bytes,
        signature_header: str
    ) -> bool:
        """Verifies HMAC signature of inbound payment callback webhooks."""
        pass

    @abstractmethod
    async def check_status(
        self,
        provider_reference: str
    ) -> Dict[str, Any]:
        """Queries the payment gateway for status update."""
        pass
