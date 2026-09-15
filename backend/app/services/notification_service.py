import logging
import smtplib
from email.mime.text import MIMEText
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.orm import Notification, User, Customer

logger = logging.getLogger("notification_service")


class SMSGatewayProvider:
    """
    Pluggable SMS Provider interface.
    Stubbed for local / PNG gateway integrations (e.g. Digicel / Telikom PNG SMS gateways).
    """

    def send_sms(self, phone_number: str, message: str) -> bool:
        # TODO: Replace stub with live PNG Telco SMS Gateway API call using settings.sms_provider_url & settings.sms_provider_api_key
        logger.info(f"[SMS STUB] Sending SMS to {phone_number}: {message}")
        return True


class NotificationService:
    @staticmethod
    async def send_notification(
        db: AsyncSession,
        title: str,
        message: str,
        user_id: Optional[Any] = None,
        customer_id: Optional[Any] = None,
        channel: str = "in_app",
        recipient_email: Optional[str] = None,
        recipient_phone: Optional[str] = None
    ) -> Notification:
        """
        Creates and persists a Notification row, and dispatches via requested channel.
        """
        notif = Notification(
            user_id=user_id,
            customer_id=customer_id,
            title=title,
            message=message,
            channel=channel,
            is_read=False
        )
        db.add(notif)
        await db.flush()

        # Handle Email Channel
        if channel == "email" or channel == "all":
            if recipient_email and settings.smtp_username:
                try:
                    msg = MIMEText(message)
                    msg["Subject"] = title
                    msg["From"] = settings.smtp_from_email
                    msg["To"] = recipient_email

                    with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
                        server.starttls()
                        server.login(settings.smtp_username, settings.smtp_password)
                        server.send_message(msg)
                except Exception as e:
                    logger.error(f"Failed to send email notification: {e}")

        # Handle SMS Channel
        if channel == "sms" or channel == "all":
            if recipient_phone:
                sms_provider = SMSGatewayProvider()
                sms_provider.send_sms(recipient_phone, f"{title}: {message}")

        return notif

    @staticmethod
    async def notify_application_submitted(db: AsyncSession, user_id: Any, customer_id: Any, app_id: str):
        await NotificationService.send_notification(
            db=db,
            user_id=user_id,
            customer_id=customer_id,
            title="Loan Application Submitted",
            message=f"Your loan application #{app_id[:8]} has been submitted and is under review.",
            channel="in_app"
        )

    @staticmethod
    async def notify_application_decision(db: AsyncSession, user_id: Any, customer_id: Any, app_id: str, decision: str):
        title = f"Loan Application {decision.replace('_', ' ').title()}"
        msg = f"Your loan application #{app_id[:8]} has been evaluated: status is now {decision}."
        await NotificationService.send_notification(
            db=db,
            user_id=user_id,
            customer_id=customer_id,
            title=title,
            message=msg,
            channel="in_app"
        )

    @staticmethod
    async def notify_disbursement(db: AsyncSession, user_id: Any, customer_id: Any, loan_id: str, amount: float):
        await NotificationService.send_notification(
            db=db,
            user_id=user_id,
            customer_id=customer_id,
            title="Loan Disbursed",
            message=f"Your loan funds of PGK {amount:.2f} (Loan #{loan_id[:8]}) have been successfully disbursed.",
            channel="in_app"
        )

    @staticmethod
    async def notify_repayment_reminder(db: AsyncSession, user_id: Any, customer_id: Any, loan_id: str, due_amount: float, due_date: str):
        await NotificationService.send_notification(
            db=db,
            user_id=user_id,
            customer_id=customer_id,
            title="Upcoming Repayment Due",
            message=f"Reminder: Repayment of PGK {due_amount:.2f} for Loan #{loan_id[:8]} is due on {due_date}.",
            channel="in_app"
        )

    @staticmethod
    async def notify_overdue(db: AsyncSession, user_id: Any, customer_id: Any, loan_id: str, amount_overdue: float, days_overdue: int):
        await NotificationService.send_notification(
            db=db,
            user_id=user_id,
            customer_id=customer_id,
            title="Account Arrears Notice",
            message=f"Urgent: Loan #{loan_id[:8]} is overdue by {days_overdue} days with PGK {amount_overdue:.2f} outstanding. Please make a payment immediately.",
            channel="in_app"
        )
