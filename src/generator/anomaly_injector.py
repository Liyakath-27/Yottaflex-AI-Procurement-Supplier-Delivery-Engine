"""
Deterministic Anomaly and Edge Case Injector.
Produces distinct, auditable ground-truth labels isolated from standard inputs.
"""
from typing import List, Dict, Any, Optional
import random
from datetime import datetime, timedelta
from src.models.entities import (
    PurchaseRequest,
    RequestLine,
    RFQ,
    SupplierQuote,
    PurchaseOrder,
    Approval,
    Budget,
    Supplier,
    GroundTruthAnomaly,
)
from src.models.enums import AnomalyType, AnomalySeverity, ApprovalDecision, QuoteStatus


class AnomalyInjector:
    def __init__(self, rng: random.Random):
        self.rng = rng
        self.ground_truth_records: List[GroundTruthAnomaly] = []
        self._anomaly_counter = 1
        self._used_rfq_ids = set()

    def _next_id(self) -> str:
        aid = f"ANO-{self._anomaly_counter:05d}"
        self._anomaly_counter += 1
        return aid

    def inject_po_without_approval(self, pos: List[PurchaseOrder]) -> int:
        """Inject POs issued without authorized approval records."""
        eligible_pos = [p for p in pos if p.approval_reference_id is not None]
        target_count = max(5, int(len(pos) * 0.02))  # ~2% of POs
        sampled = self.rng.sample(eligible_pos, min(target_count, len(eligible_pos)))

        for po in sampled:
            po.approval_reference_id = None
            self.ground_truth_records.append(
                GroundTruthAnomaly(
                    anomaly_id=self._next_id(),
                    entity_type="PurchaseOrder",
                    entity_id=po.po_id,
                    issue_type=AnomalyType.PO_WITHOUT_APPROVAL,
                    severity=AnomalySeverity.CRITICAL,
                    rule_violated="BR-001: Mandatory Approval Before PO Issuance",
                    description=(
                        f"Purchase order {po.po_id} for ${po.total_po_amount:,.2f} was issued "
                        f"without an authorized approval reference."
                    ),
                    detection_criteria="PurchaseOrder.approval_reference_id IS NULL AND request unapproved",
                    injected_at_stage="PO_GENERATION",
                    expected_audit_verdict="NON_COMPLIANT",
                )
            )
        return len(sampled)

    def inject_quote_expired_before_award(
        self, rfqs: List[RFQ], quotes_by_id: Dict[str, SupplierQuote]
    ) -> int:
        """Inject awarded quotes whose validity expired before RFQ award date."""
        awarded_rfqs = [r for r in rfqs if r.awarded_quote_id and r.award_date]
        target_count = max(4, int(len(awarded_rfqs) * 0.025))
        sampled = self.rng.sample(awarded_rfqs, min(target_count, len(awarded_rfqs)))

        for rfq in sampled:
            quote = quotes_by_id.get(rfq.awarded_quote_id)
            if not quote:
                continue
            self._used_rfq_ids.add(rfq.rfq_id)
            award_dt = datetime.fromisoformat(rfq.award_date)
            # Make quote validity end 5 to 15 days before award
            expired_dt = award_dt - timedelta(days=self.rng.randint(5, 15))
            quote.validity_end_date = expired_dt.strftime("%Y-%m-%d")

            self.ground_truth_records.append(
                GroundTruthAnomaly(
                    anomaly_id=self._next_id(),
                    entity_type="SupplierQuote",
                    entity_id=quote.quote_id,
                    issue_type=AnomalyType.QUOTE_EXPIRED_BEFORE_AWARD,
                    severity=AnomalySeverity.HIGH,
                    rule_violated="BR-002: Quote Pricing Must Be Valid At Award Date",
                    description=(
                        f"Quote {quote.quote_id} expired on {quote.validity_end_date} before "
                        f"award date {rfq.award_date} on RFQ {rfq.rfq_id}."
                    ),
                    detection_criteria="SupplierQuote.validity_end_date < RFQ.award_date",
                    injected_at_stage="QUOTE_EVALUATION",
                    expected_audit_verdict="NON_COMPLIANT",
                )
            )
        return len(sampled)

    def inject_non_cheapest_without_rationale(
        self,
        rfqs: List[RFQ],
        quotes_by_rfq: Dict[str, List[SupplierQuote]],
        quotes_by_id: Dict[str, SupplierQuote],
    ) -> int:
        """Inject awarded non-cheapest quotes that lack documented rationale."""
        eligible_rfqs = []
        for rfq in rfqs:
            if not rfq.awarded_quote_id or rfq.rfq_id in self._used_rfq_ids:
                continue
            r_quotes = quotes_by_rfq.get(rfq.rfq_id, [])
            if len(r_quotes) >= 2:
                eligible_rfqs.append((rfq, r_quotes))

        target_count = max(4, int(len(eligible_rfqs) * 0.03))
        sampled = self.rng.sample(eligible_rfqs, min(target_count, len(eligible_rfqs)))

        count = 0
        for rfq, r_quotes in sampled:
            sorted_quotes = sorted(r_quotes, key=lambda q: q.total_landed_cost_usd)
            cheapest = sorted_quotes[0]
            strictly_higher = [q for q in sorted_quotes if q.total_landed_cost_usd > (cheapest.total_landed_cost_usd + 0.01)]
            if not strictly_higher:
                continue
            expensive = strictly_higher[0]

            self._used_rfq_ids.add(rfq.rfq_id)
            rfq.awarded_quote_id = expensive.quote_id
            rfq.awarded_supplier_id = expensive.supplier_id
            expensive.quote_status = QuoteStatus.ACCEPTED
            cheapest.quote_status = QuoteStatus.REJECTED
            # Clear or set generic rationale
            expensive.award_rationale = ""

            self.ground_truth_records.append(
                GroundTruthAnomaly(
                    anomaly_id=self._next_id(),
                    entity_type="SupplierQuote",
                    entity_id=expensive.quote_id,
                    issue_type=AnomalyType.NON_CHEAPEST_WITHOUT_RATIONALE,
                    severity=AnomalySeverity.HIGH,
                    rule_violated="BR-003: Justification Required for Non-Cheapest Award",
                    description=(
                        f"Quote {expensive.quote_id} (${expensive.total_landed_cost_usd:,.2f}) "
                        f"was awarded over lower quote {cheapest.quote_id} "
                        f"(${cheapest.total_landed_cost_usd:,.2f}) without documented justification."
                    ),
                    detection_criteria="Awarded quote != lowest landed cost AND award_rationale IS EMPTY",
                    injected_at_stage="SUPPLIER_AWARD",
                    expected_audit_verdict="NON_COMPLIANT",
                )
            )
            count += 1
        return count

    def inject_inactive_supplier(
        self,
        suppliers: List[Supplier],
        pos: List[PurchaseOrder],
        quotes: List[SupplierQuote],
    ) -> int:
        """Inject POs and Quotes issued to inactive suppliers."""
        target_count = max(3, int(len(suppliers) * 0.04))
        # Choose some suppliers to mark inactive
        sampled_suppliers = self.rng.sample(suppliers, target_count)
        for s in sampled_suppliers:
            s.is_active = False

        inactive_ids = {s.supplier_id for s in sampled_suppliers}
        affected_pos = [p for p in pos if p.supplier_id in inactive_ids]

        count = 0
        for po in affected_pos:
            self.ground_truth_records.append(
                GroundTruthAnomaly(
                    anomaly_id=self._next_id(),
                    entity_type="PurchaseOrder",
                    entity_id=po.po_id,
                    issue_type=AnomalyType.INACTIVE_SUPPLIER,
                    severity=AnomalySeverity.CRITICAL,
                    rule_violated="BR-004: Prohibited Transaction with Inactive Supplier",
                    description=(
                        f"Purchase order {po.po_id} was awarded/issued to deactivated supplier "
                        f"{po.supplier_id}."
                    ),
                    detection_criteria="PurchaseOrder.supplier_id -> Supplier.is_active == False",
                    injected_at_stage="PO_ISSUANCE",
                    expected_audit_verdict="NON_COMPLIANT",
                )
            )
            count += 1
        return count

    def inject_budget_overrun(
        self,
        budgets: List[Budget],
        requests_by_budget: Dict[str, List[PurchaseRequest]],
    ) -> int:
        """Inject budget overrun by deliberately modifying budget allocation downward below spend."""
        eligible_budgets = [b for b in budgets if (b.committed_amount + b.spent_amount) > 10000.0]
        target_count = max(2, int(len(budgets) * 0.10))
        sampled = self.rng.sample(eligible_budgets, min(target_count, len(eligible_budgets)))

        for b in sampled:
            utilized = b.committed_amount + b.spent_amount
            # Force allocation to be 15-30% lower than utilized
            overrun_amount = round(utilized * self.rng.uniform(0.15, 0.30), 2)
            b.allocated_amount = round(utilized - overrun_amount, 2)
            b.remaining_balance = round(b.allocated_amount - utilized, 2)

            self.ground_truth_records.append(
                GroundTruthAnomaly(
                    anomaly_id=self._next_id(),
                    entity_type="Budget",
                    entity_id=b.budget_id,
                    issue_type=AnomalyType.BUDGET_OVERRUN,
                    severity=AnomalySeverity.HIGH,
                    rule_violated="BR-005: Budget Allocation Limit Exceeded",
                    description=(
                        f"Budget {b.budget_id} ({b.category.value}) is overrun by ${overrun_amount:,.2f}. "
                        f"Allocated: ${b.allocated_amount:,.2f}, Utilized: ${utilized:,.2f}."
                    ),
                    detection_criteria="(committed_amount + spent_amount) > allocated_amount",
                    injected_at_stage="BUDGET_MANAGEMENT",
                    expected_audit_verdict="NON_COMPLIANT",
                )
            )
        return len(sampled)

    def inject_duplicate_requests(
        self,
        requests: List[PurchaseRequest],
        request_lines_by_pr: Dict[str, List[RequestLine]],
    ) -> int:
        """Inject near-duplicate requests submitted shortly after original."""
        target_count = max(4, int(len(requests) * 0.02))
        sampled = self.rng.sample(requests[:len(requests)//2], min(target_count, len(requests)//2))

        count = 0
        for orig_pr in sampled:
            orig_dt = datetime.fromisoformat(orig_pr.request_date)
            dup_dt = orig_dt + timedelta(hours=self.rng.randint(2, 36))

            dup_pr_id = f"PR-2026-{100000 + len(requests) + count:06d}"
            dup_pr = PurchaseRequest(
                request_id=dup_pr_id,
                requester_id=orig_pr.requester_id,
                department_id=orig_pr.department_id,
                budget_id=orig_pr.budget_id,
                request_date=dup_dt.isoformat(),
                required_date=orig_pr.required_date,
                status=orig_pr.status,
                category=orig_pr.category,
                priority=orig_pr.priority,
                total_estimated_amount=orig_pr.total_estimated_amount,
                currency=orig_pr.currency,
                procurement_method=orig_pr.procurement_method,
                single_source_justification=orig_pr.single_source_justification,
                is_split_purchase=False,
                approval_tier_required=orig_pr.approval_tier_required,
            )
            requests.append(dup_pr)

            # Duplicate lines
            orig_lines = request_lines_by_pr.get(orig_pr.request_id, [])
            request_lines_by_pr[dup_pr_id] = []
            for line_idx, ol in enumerate(orig_lines, start=1):
                dup_line = RequestLine(
                    line_id=f"{dup_pr_id}-L{line_idx:02d}",
                    request_id=dup_pr_id,
                    line_number=line_idx,
                    item_description=ol.item_description,
                    item_category=ol.item_category,
                    quantity=ol.quantity,
                    unit_of_measure=ol.unit_of_measure,
                    estimated_unit_price=ol.estimated_unit_price,
                    estimated_line_total=ol.estimated_line_total,
                )
                request_lines_by_pr[dup_pr_id].append(dup_line)

            self.ground_truth_records.append(
                GroundTruthAnomaly(
                    anomaly_id=self._next_id(),
                    entity_type="PurchaseRequest",
                    entity_id=dup_pr_id,
                    issue_type=AnomalyType.DUPLICATE_REQUEST,
                    severity=AnomalySeverity.MEDIUM,
                    rule_violated="BR-006: Duplicate Purchase Request Detected",
                    description=(
                        f"Purchase request {dup_pr_id} submitted by {dup_pr.requester_id} is a duplicate of "
                        f"{orig_pr.request_id} within {(dup_dt - orig_dt).total_seconds()/3600:.1f} hours."
                    ),
                    detection_criteria="Exact item/quantity match by same requester/dept within 72h",
                    injected_at_stage="REQUEST_CREATION",
                    expected_audit_verdict="FLAGGED_FOR_REVIEW",
                )
            )
            count += 1
        return count

    def inject_quote_currency_mismatch(self, quotes: List[SupplierQuote]) -> int:
        """Inject foreign currency quotes whose USD landed cost omitted the exchange rate."""
        eligible_quotes = [
            q for q in quotes
            if q.currency.value in ["EUR", "GBP"] and abs(q.exchange_rate_to_usd - 1.0) > 0.05
        ]
        target_count = max(4, int(len(eligible_quotes) * 0.05))
        sampled = self.rng.sample(eligible_quotes, min(target_count, len(eligible_quotes)))

        for q in sampled:
            # Overwrite total_landed_cost_usd with 1:1 base without multiplying FX
            raw_sum = q.base_amount + q.freight_cost + q.tax_duty_amount - q.discount_amount
            q.total_landed_cost_usd = round(raw_sum, 2)

            self.ground_truth_records.append(
                GroundTruthAnomaly(
                    anomaly_id=self._next_id(),
                    entity_type="SupplierQuote",
                    entity_id=q.quote_id,
                    issue_type=AnomalyType.QUOTE_CURRENCY_MISMATCH,
                    severity=AnomalySeverity.HIGH,
                    rule_violated="BR-007: Foreign Currency Conversion Omission",
                    description=(
                        f"Supplier quote {q.quote_id} in {q.currency.value} with exchange rate "
                        f"{q.exchange_rate_to_usd} was calculated as 1:1 USD (${q.total_landed_cost_usd:,.2f}) "
                        f"omitting currency conversion."
                    ),
                    detection_criteria="total_landed_cost_usd == sum(quote_currency) with FX != 1.0",
                    injected_at_stage="QUOTE_ENTRY",
                    expected_audit_verdict="NON_COMPLIANT",
                )
            )
        return len(sampled)
