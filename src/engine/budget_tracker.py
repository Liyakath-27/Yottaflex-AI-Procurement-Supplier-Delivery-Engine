"""
Budget Allocation and Encumbrance Tracking Engine.
"""
from typing import Dict, Optional, Tuple
from src.models.entities import Budget
from src.models.enums import BudgetStatus


class BudgetTracker:
    def __init__(self, budgets: Dict[str, Budget]):
        self.budgets = budgets

    def check_availability(self, budget_id: str, amount: float) -> Tuple[bool, float, float]:
        """
        Check if requested amount is available within budget.
        Returns: (is_available, remaining_balance, shortfall)
        """
        budget = self.budgets.get(budget_id)
        if not budget:
            return False, 0.0, amount

        remaining = budget.allocated_amount - (budget.committed_amount + budget.spent_amount)
        if amount <= remaining:
            return True, remaining, 0.0
        else:
            return False, remaining, amount - remaining

    def commit_budget(self, budget_id: str, amount: float) -> bool:
        """Encumber budget for an approved PR / issued PO."""
        budget = self.budgets.get(budget_id)
        if not budget:
            return False

        budget.committed_amount = round(budget.committed_amount + amount, 2)
        budget.remaining_balance = round(
            budget.allocated_amount - (budget.committed_amount + budget.spent_amount), 2
        )
        if budget.remaining_balance <= 0.0:
            budget.status = BudgetStatus.DEPLETED
        return True

    def spend_budget(self, budget_id: str, amount: float) -> bool:
        """Convert committed budget to realized spend upon delivery."""
        budget = self.budgets.get(budget_id)
        if not budget:
            return False

        # Release commitment and add to spend
        budget.committed_amount = round(max(0.0, budget.committed_amount - amount), 2)
        budget.spent_amount = round(budget.spent_amount + amount, 2)
        budget.remaining_balance = round(
            budget.allocated_amount - (budget.committed_amount + budget.spent_amount), 2
        )
        if budget.remaining_balance <= 0.0:
            budget.status = BudgetStatus.DEPLETED
        return True

    def recalculate_all(self):
        """Ensure consistency across all tracked budgets."""
        for b in self.budgets.values():
            b.remaining_balance = round(b.allocated_amount - (b.committed_amount + b.spent_amount), 2)
            if b.remaining_balance <= 0:
                b.status = BudgetStatus.DEPLETED
            elif b.status == BudgetStatus.DEPLETED and b.remaining_balance > 0:
                b.status = BudgetStatus.ACTIVE

