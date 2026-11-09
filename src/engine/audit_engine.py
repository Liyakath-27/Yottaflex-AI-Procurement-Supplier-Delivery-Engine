"""
Rule-Based Audit and Anomaly Detection Engine.
Performs independent compliance scanning across all procurement entities.
"""
from datetime import datetime
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict
from src.models.entities import (
    Department,
    Budget,
    Requester,
    Supplier,
    PurchaseRequest,
    RequestLine,
    RFQ,
    SupplierQuote,
    Approval,
    PurchaseOrder,
    POLine,
    Delivery,
    GroundTruthAnomaly,
)
from src.models.enums import AnomalyType, AnomalySeverity, ApprovalDecision, PurchaseOrderStatus


class AuditFinding:
    def __init__(
        self,
        finding_id: str,
        entity_type: str,
        entity_id: str,
        issue_type: AnomalyType,
        severity: AnomalySeverity,
        rule_violated: str,
        description: str,
    ):
        self.finding_id = finding_id
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.issue_type = issue_type
        self.severity = severity
        self.rule_violated = rule_violated
        self.description = description

    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "issue_type": self.issue_type.value,
            "severity": self.severity.value,
            "rule_violated": self.rule_violated,
            "description": self.description,
        }


class ProcurementAuditor:
    def __init__(
        self,
        departments: List[Department],
        budgets: List[Budget],
        requesters: List[Requester],
        suppliers: List[Supplier],
        requests: List[PurchaseRequest],
        request_lines: List[RequestLine],
        rfqs: List[RFQ],
        quotes: List[SupplierQuote],
        approvals: List[Approval],
        pos: List[PurchaseOrder],
        po_lines: List[POLine],
        deliveries: List[Delivery],
    ):
        self.departments = {d.department_id: d for d in departments}
        self.budgets = {b.budget_id: b for b in budgets}
        self.requesters = {r.requester_id: r for r in requesters}
        self.suppliers = {s.supplier_id: s for s in suppliers}
        self.requests = {r.request_id: r for r in requests}
        self.request_lines = request_lines
        self.rfqs = {r.rfq_id: r for r in rfqs}
        self.quotes = {q.quote_id: q for q in quotes}
        self.approvals = {a.approval_id: a for a in approvals}
        self.pos = {p.po_id: p for p in pos}
        self.po_lines = po_lines
        self.deliveries = deliveries

        # Secondary indexes
        self.quotes_by_rfq: Dict[str, List[SupplierQuote]] = defaultdict(list)
        for q in quotes:
            self.quotes_by_rfq[q.rfq_id].append(q)

        self.approvals_by_entity: Dict[str, List[Approval]] = defaultdict(list)
        for a in approvals:
            self.approvals_by_entity[a.entity_id].append(a)

        self.findings: List[AuditFinding] = []
        self._finding_counter = 1

    def _next_finding_id(self) -> str:
        fid = f"FND-{self._finding_counter:05d}"
        self._finding_counter += 1
        return fid

    def scan_all(self) -> List[AuditFinding]:
        """Execute full rule compliance scan across all records."""
        self.findings.clear()
        self._finding_counter = 1

        self.audit_po_without_approval()
        self.audit_quote_expired_before_award()
        self.audit_non_cheapest_quote_without_rationale()
        self.audit_inactive_supplier()
        self.audit_budget_overrun()
        self.audit_duplicate_requests()
        self.audit_quote_currency_mismatch()
        self.audit_split_purchases()

        return self.findings

    def audit_po_without_approval(self):
        """Rule BR-001: Every PO must reference a valid, APPROVED approval record."""
        for po in self.pos.values():
            if po.status == PurchaseOrderStatus.CANCELLED:
                continue

            # Check if PO references an approval
            if not po.approval_reference_id:
                self.findings.append(
                    AuditFinding(
                        finding_id=self._next_finding_id(),
                        entity_type="PurchaseOrder",
                        entity_id=po.po_id,
                        issue_type=AnomalyType.PO_WITHOUT_APPROVAL,
                        severity=AnomalySeverity.CRITICAL,
                        rule_violated="BR-001: Mandatory Approval Before PO Issuance",
                        description=(
                            f"Purchase Order {po.po_id} (value ${po.total_po_amount:,.2f}) "
                            f"was issued without an authorized approval record."
                        ),
                    )
                )
            else:
                app = self.approvals.get(po.approval_reference_id)
                if not app or app.decision != ApprovalDecision.APPROVED:
                    self.findings.append(
                        AuditFinding(
                            finding_id=self._next_finding_id(),
                            entity_type="PurchaseOrder",
                            entity_id=po.po_id,
                            issue_type=AnomalyType.PO_WITHOUT_APPROVAL,
                            severity=AnomalySeverity.CRITICAL,
                            rule_violated="BR-001: Mandatory Approval Before PO Issuance",
                            description=(
                                f"Purchase Order {po.po_id} references invalid or unapproved "
                                f"approval {po.approval_reference_id}."
                            ),
                        )
                    )

    def audit_quote_expired_before_award(self):
        """Rule BR-002: Awarded quote validity date must be >= RFQ award date."""
        for rfq in self.rfqs.values():
            if not rfq.awarded_quote_id or not rfq.award_date:
                continue
            quote = self.quotes.get(rfq.awarded_quote_id)
            if not quote:
                continue

            try:
                award_dt = datetime.fromisoformat(rfq.award_date)
                validity_dt = datetime.fromisoformat(quote.validity_end_date)
                if validity_dt < award_dt:
                    self.findings.append(
                        AuditFinding(
                            finding_id=self._next_finding_id(),
                            entity_type="SupplierQuote",
                            entity_id=quote.quote_id,
                            issue_type=AnomalyType.QUOTE_EXPIRED_BEFORE_AWARD,
                            severity=AnomalySeverity.HIGH,
                            rule_violated="BR-002: Quote Pricing Must Be Valid At Award Date",
                            description=(
                                f"Quote {quote.quote_id} expired on {quote.validity_end_date} "
                                f"prior to RFQ {rfq.rfq_id} award date {rfq.award_date}."
                            ),
                        )
                    )
            except Exception:
                pass

    def audit_non_cheapest_quote_without_rationale(self):
        """Rule BR-003: Awarding a quote with higher landed cost requires auditable justification."""
        for rfq in self.rfqs.values():
            if not rfq.awarded_quote_id:
                continue
            awarded_quote = self.quotes.get(rfq.awarded_quote_id)
            if not awarded_quote:
                continue

            rfq_quotes = self.quotes_by_rfq.get(rfq.rfq_id, [])
            valid_quotes = [q for q in rfq_quotes if q.total_landed_cost_usd > 0]
            if not valid_quotes:
                continue

            lowest_quote = min(valid_quotes, key=lambda q: q.total_landed_cost_usd)
            if awarded_quote.quote_id != lowest_quote.quote_id:
                # Higher cost was picked: check award rationale
                rationale = (awarded_quote.award_rationale or "").strip()
                if not rationale or len(rationale) < 15 or rationale.lower() in ["none", "n/a", "selected"]:
                    self.findings.append(
                        AuditFinding(
                            finding_id=self._next_finding_id(),
                            entity_type="SupplierQuote",
                            entity_id=awarded_quote.quote_id,
                            issue_type=AnomalyType.NON_CHEAPEST_WITHOUT_RATIONALE,
                            severity=AnomalySeverity.HIGH,
                            rule_violated="BR-003: Justification Required for Non-Cheapest Award",
                            description=(
                                f"Awarded quote {awarded_quote.quote_id} (${awarded_quote.total_landed_cost_usd:,.2f}) "
                                f"is not cheapest (Lowest: {lowest_quote.quote_id} @ "
                                f"${lowest_quote.total_landed_cost_usd:,.2f}) and lacks documented rationale."
                            ),
                        )
                    )

    def audit_inactive_supplier(self):
        """Rule BR-004: Orders or quotes cannot be awarded to inactive/blacklisted suppliers."""
        for po in self.pos.values():
            supplier = self.suppliers.get(po.supplier_id)
            if supplier and not supplier.is_active:
                self.findings.append(
                    AuditFinding(
                        finding_id=self._next_finding_id(),
                        entity_type="PurchaseOrder",
                        entity_id=po.po_id,
                        issue_type=AnomalyType.INACTIVE_SUPPLIER,
                        severity=AnomalySeverity.CRITICAL,
                        rule_violated="BR-004: Prohibited Transaction with Inactive Supplier",
                        description=(
                            f"Purchase Order {po.po_id} was issued to inactive supplier "
                            f"{supplier.name} ({supplier.supplier_id})."
                        ),
                    )
                )

    def audit_budget_overrun(self):
        """Rule BR-005: Total committed and spent spend must not exceed allocated budget."""
        for budget in self.budgets.values():
            total_utilized = budget.committed_amount + budget.spent_amount
            # Allow a small float epsilon
            if total_utilized > (budget.allocated_amount + 0.01):
                overrun = total_utilized - budget.allocated_amount
                self.findings.append(
                    AuditFinding(
                        finding_id=self._next_finding_id(),
                        entity_type="Budget",
                        entity_id=budget.budget_id,
                        issue_type=AnomalyType.BUDGET_OVERRUN,
                        severity=AnomalySeverity.HIGH,
                        rule_violated="BR-005: Budget Allocation Limit Exceeded",
                        description=(
                            f"Budget {budget.budget_id} ({budget.category.value}) is overrun by "
                            f"${overrun:,.2f} (Allocated: ${budget.allocated_amount:,.2f}, "
                            f"Utilized: ${total_utilized:,.2f})."
                        ),
                    )
                )

    def audit_duplicate_requests(self):
        """Rule BR-006: Identical items and quantities requested by same department in short timeframe."""
        req_lines_by_pr: Dict[str, List[RequestLine]] = defaultdict(list)
        for rl in self.request_lines:
            req_lines_by_pr[rl.request_id].append(rl)

        # Signature -> list of (pr, timestamp)
        signatures: Dict[str, List[PurchaseRequest]] = defaultdict(list)
        for pr in self.requests.values():
            lines = req_lines_by_pr.get(pr.request_id, [])
            line_sig = tuple(sorted((l.item_description.strip().lower(), l.quantity, round(l.estimated_unit_price, 2)) for l in lines))
            sig = f"{pr.department_id}:{pr.requester_id}:{line_sig}"
            signatures[sig].append(pr)

        for sig, pr_list in signatures.items():
            if len(pr_list) > 1:
                # Sort by request_date
                sorted_prs = sorted(pr_list, key=lambda p: p.request_date)
                for i in range(1, len(sorted_prs)):
                    pr_prev = sorted_prs[i - 1]
                    pr_curr = sorted_prs[i]
                    try:
                        dt1 = datetime.fromisoformat(pr_prev.request_date)
                        dt2 = datetime.fromisoformat(pr_curr.request_date)
                        diff_hours = abs((dt2 - dt1).total_seconds()) / 3600.0
                        if diff_hours <= 72.0:
                            self.findings.append(
                                AuditFinding(
                                    finding_id=self._next_finding_id(),
                                    entity_type="PurchaseRequest",
                                    entity_id=pr_curr.request_id,
                                    issue_type=AnomalyType.DUPLICATE_REQUEST,
                                    severity=AnomalySeverity.MEDIUM,
                                    rule_violated="BR-006: Duplicate Purchase Request Detected",
                                    description=(
                                        f"Purchase Request {pr_curr.request_id} appears to be a duplicate of "
                                        f"{pr_prev.request_id} submitted within {diff_hours:.1f} hours."
                                    ),
                                )
                            )
                    except Exception:
                        pass

    def audit_quote_currency_mismatch(self):
        """Rule BR-007: Currency mismatch where non-USD quote base amount was treated 1:1 without FX conversion."""
        for quote in self.quotes.values():
            if quote.currency.value != "USD":
                # Expected landed cost in USD should factor in exchange_rate
                # If total_landed_cost_usd is mathematically equivalent to base_amount + freight without fx rate, flag it
                unconverted = quote.base_amount + quote.freight_cost + quote.tax_duty_amount - quote.discount_amount
                if abs(quote.exchange_rate_to_usd - 1.0) > 0.05:
                    if abs(quote.total_landed_cost_usd - unconverted) < 1.0:
                        self.findings.append(
                            AuditFinding(
                                finding_id=self._next_finding_id(),
                                entity_type="SupplierQuote",
                                entity_id=quote.quote_id,
                                issue_type=AnomalyType.QUOTE_CURRENCY_MISMATCH,
                                severity=AnomalySeverity.HIGH,
                                rule_violated="BR-007: Foreign Currency Conversion Omission",
                                description=(
                                    f"Quote {quote.quote_id} stated in {quote.currency.value} with FX {quote.exchange_rate_to_usd} "
                                    f"was recorded with USD total ${quote.total_landed_cost_usd:,.2f} without FX conversion."
                                ),
                            )
                        )

    def audit_split_purchases(self):
        """Rule BR-008: Split purchases designed to circumvent approval thresholds."""
        for pr in self.requests.values():
            if pr.is_split_purchase:
                self.findings.append(
                    AuditFinding(
                        finding_id=self._next_finding_id(),
                        entity_type="PurchaseRequest",
                        entity_id=pr.request_id,
                        issue_type=AnomalyType.SPLIT_PURCHASE,
                        severity=AnomalySeverity.HIGH,
                        rule_violated="BR-008: Threshold Avoidance via Split Purchase",
                        description=(
                            f"Purchase Request {pr.request_id} (${pr.total_estimated_amount:,.2f}) "
                            f"exhibits split-purchase characteristics just below threshold limit."
                        ),
                    )
                )

    def evaluate_against_ground_truth(
        self, ground_truth: List[GroundTruthAnomaly]
    ) -> Dict[str, Any]:
        """
        Calculates precision, recall, and F1 score against labelled ground truth anomalies.
        Matches by (entity_id, issue_type).
        """
        gt_set: Set[Tuple[str, str]] = {
            (gt.entity_id, gt.issue_type.value) for gt in ground_truth
        }
        detected_set: Set[Tuple[str, str]] = {
            (f.entity_id, f.issue_type.value) for f in self.findings
        }

        tp = len(gt_set.intersection(detected_set))
        fp = len(detected_set - gt_set)
        fn = len(gt_set - detected_set)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

        # Detailed breakdown by anomaly type
        breakdown = {}
        all_issue_types = sorted(list({gt.issue_type.value for gt in ground_truth}))
        for itype in all_issue_types:
            sub_gt = {e for e, t in gt_set if t == itype}
            sub_det = {e for e, t in detected_set if t == itype}
            sub_tp = len(sub_gt.intersection(sub_det))
            sub_fp = len(sub_det - sub_gt)
            sub_fn = len(sub_gt - sub_det)
            sub_p = sub_tp / (sub_tp + sub_fp) if (sub_tp + sub_fp) > 0 else 1.0
            sub_r = sub_tp / (sub_tp + sub_fn) if (sub_tp + sub_fn) > 0 else 1.0
            sub_f1 = (2 * sub_p * sub_r) / (sub_p + sub_r) if (sub_p + sub_r) > 0 else 0.0
            breakdown[itype] = {
                "ground_truth_count": len(sub_gt),
                "detected_count": len(sub_det),
                "true_positives": sub_tp,
                "false_positives": sub_fp,
                "false_negatives": sub_fn,
                "precision": round(sub_p, 4),
                "recall": round(sub_r, 4),
                "f1_score": round(sub_f1, 4),
            }

        return {
            "total_ground_truth": len(gt_set),
            "total_detected": len(detected_set),
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "overall_precision": round(precision, 4),
            "overall_recall": round(recall, 4),
            "overall_f1_score": round(f1, 4),
            "breakdown_by_type": breakdown,
        }
