"""
Approval Matrix and Authority Threshold Engine.
"""
from typing import Tuple, List, Optional
from src.models.enums import ApprovalTier, ApprovalDecision, RequesterRole
from src.models.entities import Requester, PurchaseRequest, Budget


def get_required_tier(amount: float) -> ApprovalTier:
    """Return required approval tier based on estimated amount."""
    if amount < 1000.0:
        return ApprovalTier.TIER_1_MANAGER
    elif amount < 10000.0:
        return ApprovalTier.TIER_2_DEPT_HEAD
    elif amount < 50000.0:
        return ApprovalTier.TIER_3_FINANCE_DIR
    else:
        return ApprovalTier.TIER_4_EXECUTIVE


def get_tier_min_limit(tier: ApprovalTier) -> float:
    """Minimum approval limit required for a tier."""
    if tier == ApprovalTier.TIER_1_MANAGER:
        return 1000.0
    elif tier == ApprovalTier.TIER_2_DEPT_HEAD:
        return 10000.0
    elif tier == ApprovalTier.TIER_3_FINANCE_DIR:
        return 50000.0
    else:
        return 250000.0


def can_approve(approver: Requester, amount: float) -> bool:
    """Determine if approver has sufficient signing limit."""
    return approver.is_active and approver.approval_limit >= amount


def select_eligible_approver(
    tier: ApprovalTier,
    department_id: str,
    requesters: List[Requester],
    pr_requester_id: Optional[str] = None,
) -> Optional[Requester]:
    """
    Select an active approver matching or exceeding the tier limit.
    Enforces separation of duties: requester cannot approve their own PR.
    """
    min_limit = get_tier_min_limit(tier)

    # First attempt: department matching approver
    dept_candidates = [
        r for r in requesters
        if r.department_id == department_id
        and r.is_active
        and r.approval_limit >= min_limit
        and r.requester_id != pr_requester_id
    ]
    if dept_candidates:
        return sorted(dept_candidates, key=lambda r: r.approval_limit)[0]

    # Global pool fallback (Directors, VPs, Finance)
    global_candidates = [
        r for r in requesters
        if r.is_active
        and r.approval_limit >= min_limit
        and r.requester_id != pr_requester_id
    ]
    if global_candidates:
        return sorted(global_candidates, key=lambda r: r.approval_limit)[0]

    return None

