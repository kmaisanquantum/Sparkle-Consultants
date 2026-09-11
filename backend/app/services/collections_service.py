from datetime import date, datetime, timezone
from typing import Dict, Any

class CollectionsService:
    @staticmethod
    def determine_stage(days_overdue: int) -> str:
        if days_overdue <= 0:
            return "current"
        elif days_overdue == 1:
            return "due_today"
        elif 1 < days_overdue <= 7:
            return "overdue_1_7"
        elif 7 < days_overdue <= 30:
            return "overdue_8_30"
        elif 30 < days_overdue <= 60:
            return "overdue_31_60"
        elif 60 < days_overdue <= 90:
            return "overdue_61_90"
        elif 90 < days_overdue <= 120:
            return "serious_arrears"
        elif 120 < days_overdue <= 180:
            return "default"
        else:
            return "recovery"

    @staticmethod
    def evaluate_collection_status(due_date: date, outstanding_balance: float) -> Dict[str, Any]:
        today = date.today()
        if due_date >= today or outstanding_balance <= 0:
            days_overdue = 0
        else:
            days_overdue = (today - due_date).days

        stage = CollectionsService.determine_stage(days_overdue)
        return {
            "days_overdue": days_overdue,
            "stage": stage,
            "amount_overdue": outstanding_balance if days_overdue > 0 else 0.0,
            "requires_escalation": days_overdue > 30
        }
