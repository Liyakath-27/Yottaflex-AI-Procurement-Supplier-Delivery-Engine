"""
Comprehensive Data Validation and Integrity Suite.
Performs PK uniqueness, FK referential integrity, enum compliance,
chronological ordering, arithmetic reconciliation, and lifecycle checks.
"""
from typing import Dict, Any, List, Set, Tuple
from datetime import datetime
from collections import Counter
from src.generator.synth_generator import ProcurementDataBundle
from src.engine.audit_engine import ProcurementAuditor


class ValidationResult:
    def __init__(self):
        self.is_valid: bool = True
        self.total_checks: int = 0
        self.passed_checks: int = 0
        self.failed_checks: int = 0
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.metrics: Dict[str, Any] = {}

    def record_pass(self, check_name: str):
        self.total_checks += 1
        self.passed_checks += 1

    def record_fail(self, check_name: str, message: str):
        self.total_checks += 1
        self.failed_checks += 1
        self.is_valid = False
        self.errors.append(f"[{check_name}] {message}")

    def record_warning(self, check_name: str, message: str):
        self.warnings.append(f"[{check_name}] {message}")


class DatasetValidator:
    def __init__(self, bundle: ProcurementDataBundle):
        self.bundle = bundle
        self.result = ValidationResult()

    def run_all_validations(self) -> ValidationResult:
        """Execute full validation test suite."""
        self.validate_primary_keys()
        self.validate_foreign_keys()
        self.validate_enums()
        self.validate_chronology()
        self.validate_arithmetic_reconciliation()
        self.validate_lifecycle_states()
        self.validate_audit_engine_accuracy()
        return self.result

    def validate_primary_keys(self):
        """Verify 100% primary key uniqueness across all tables."""
        tables = [
            ("departments", [d.department_id for d in self.bundle.departments]),
            ("budgets", [b.budget_id for b in self.bundle.budgets]),
            ("requesters", [r.requester_id for r in self.bundle.requesters]),
            ("suppliers", [s.supplier_id for s in self.bundle.suppliers]),
            ("purchase_requests", [p.request_id for p in self.bundle.purchase_requests]),
            ("request_lines", [l.line_id for l in self.bundle.request_lines]),
            ("rfqs", [r.rfq_id for r in self.bundle.rfqs]),
            ("supplier_quotes", [q.quote_id for q in self.bundle.supplier_quotes]),
            ("quote_lines", [l.quote_line_id for l in self.bundle.quote_lines]),
            ("approvals", [a.approval_id for a in self.bundle.approvals]),
            ("purchase_orders", [p.po_id for p in self.bundle.purchase_orders]),
            ("po_lines", [l.po_line_id for l in self.bundle.po_lines]),
            ("deliveries", [d.delivery_id for d in self.bundle.deliveries]),
            ("audit_events", [e.event_id for e in self.bundle.audit_events]),
            ("ground_truth", [g.anomaly_id for g in self.bundle.ground_truth]),
        ]

        for table_name, pk_list in tables:
            total = len(pk_list)
            unique = len(set(pk_list))
            if total == unique:
                self.result.record_pass(f"PK_UNIQUENESS_{table_name.upper()}")
            else:
                duplicates = [item for item, count in Counter(pk_list).items() if count > 1]
                self.result.record_fail(
                    f"PK_UNIQUENESS_{table_name.upper()}",
                    f"Found {total - unique} duplicate primary keys in {table_name}: {duplicates[:5]}",
                )

    def validate_foreign_keys(self):
        """Verify referential integrity across all relationships."""
        dept_ids = {d.department_id for d in self.bundle.departments}
        budget_ids = {b.budget_id for b in self.bundle.budgets}
        req_ids = {r.requester_id for r in self.bundle.requesters}
        supp_ids = {s.supplier_id for s in self.bundle.suppliers}
        pr_ids = {p.request_id for p in self.bundle.purchase_requests}
        rfq_ids = {r.rfq_id for r in self.bundle.rfqs}
        quote_ids = {q.quote_id for q in self.bundle.supplier_quotes}
        po_ids = {p.po_id for p in self.bundle.purchase_orders}
        app_ids = {a.approval_id for a in self.bundle.approvals}

        # 1. Budget -> Department
        for b in self.bundle.budgets:
            if b.department_id not in dept_ids:
                self.result.record_fail("FK_BUDGET_DEPT", f"Budget {b.budget_id} references invalid dept {b.department_id}")
        self.result.record_pass("FK_BUDGET_DEPT")

        # 2. Requester -> Department
        for r in self.bundle.requesters:
            if r.department_id not in dept_ids:
                self.result.record_fail("FK_REQUESTER_DEPT", f"Requester {r.requester_id} references invalid dept {r.department_id}")
        self.result.record_pass("FK_REQUESTER_DEPT")

        # 3. PurchaseRequest -> Requester, Department, Budget
        for pr in self.bundle.purchase_requests:
            if pr.requester_id not in req_ids:
                self.result.record_fail("FK_PR_REQUESTER", f"PR {pr.request_id} references invalid requester {pr.requester_id}")
            if pr.department_id not in dept_ids:
                self.result.record_fail("FK_PR_DEPT", f"PR {pr.request_id} references invalid dept {pr.department_id}")
            if pr.budget_id not in budget_ids:
                self.result.record_fail("FK_PR_BUDGET", f"PR {pr.request_id} references invalid budget {pr.budget_id}")
        self.result.record_pass("FK_PR_PARENTS")

        # 4. RequestLine -> PurchaseRequest
        for rl in self.bundle.request_lines:
            if rl.request_id not in pr_ids:
                self.result.record_fail("FK_REQLINE_PR", f"RequestLine {rl.line_id} references non-existent PR {rl.request_id}")
        self.result.record_pass("FK_REQLINE_PR")

        # 5. RFQ -> PurchaseRequest
        for rfq in self.bundle.rfqs:
            if rfq.request_id not in pr_ids:
                self.result.record_fail("FK_RFQ_PR", f"RFQ {rfq.rfq_id} references invalid PR {rfq.request_id}")
            if rfq.awarded_supplier_id and rfq.awarded_supplier_id not in supp_ids:
                self.result.record_fail("FK_RFQ_SUPPLIER", f"RFQ {rfq.rfq_id} references invalid supplier {rfq.awarded_supplier_id}")
            if rfq.awarded_quote_id and rfq.awarded_quote_id not in quote_ids:
                self.result.record_fail("FK_RFQ_QUOTE", f"RFQ {rfq.rfq_id} references invalid quote {rfq.awarded_quote_id}")
        self.result.record_pass("FK_RFQ_RELATIONS")

        # 6. SupplierQuote -> RFQ, Supplier
        for q in self.bundle.supplier_quotes:
            if q.rfq_id not in rfq_ids:
                self.result.record_fail("FK_QUOTE_RFQ", f"Quote {q.quote_id} references invalid RFQ {q.rfq_id}")
            if q.supplier_id not in supp_ids:
                self.result.record_fail("FK_QUOTE_SUPPLIER", f"Quote {q.quote_id} references invalid supplier {q.supplier_id}")
        self.result.record_pass("FK_QUOTE_RELATIONS")

        # 7. QuoteLine -> SupplierQuote
        for ql in self.bundle.quote_lines:
            if ql.quote_id not in quote_ids:
                self.result.record_fail("FK_QUOTELINE_QUOTE", f"QuoteLine {ql.quote_line_id} references invalid quote {ql.quote_id}")
        self.result.record_pass("FK_QUOTELINE_QUOTE")

        # 8. PurchaseOrder -> PR, Supplier, RFQ, Quote
        for po in self.bundle.purchase_orders:
            if po.request_id not in pr_ids:
                self.result.record_fail("FK_PO_PR", f"PO {po.po_id} references invalid PR {po.request_id}")
            if po.supplier_id not in supp_ids:
                self.result.record_fail("FK_PO_SUPPLIER", f"PO {po.po_id} references invalid supplier {po.supplier_id}")
            if po.rfq_id and po.rfq_id not in rfq_ids:
                self.result.record_fail("FK_PO_RFQ", f"PO {po.po_id} references invalid RFQ {po.rfq_id}")
            if po.quote_id and po.quote_id not in quote_ids:
                self.result.record_fail("FK_PO_QUOTE", f"PO {po.po_id} references invalid quote {po.quote_id}")
            if po.approval_reference_id and po.approval_reference_id not in app_ids:
                self.result.record_fail("FK_PO_APPROVAL", f"PO {po.po_id} references invalid approval {po.approval_reference_id}")
        self.result.record_pass("FK_PO_RELATIONS")

        # 9. POLine -> PurchaseOrder
        for pl in self.bundle.po_lines:
            if pl.po_id not in po_ids:
                self.result.record_fail("FK_POLINE_PO", f"POLine {pl.po_line_id} references non-existent PO {pl.po_id}")
        self.result.record_pass("FK_POLINE_PO")

        # 10. Delivery -> PO, Requester
        for deliv in self.bundle.deliveries:
            if deliv.po_id not in po_ids:
                self.result.record_fail("FK_DELIVERY_PO", f"Delivery {deliv.delivery_id} references non-existent PO {deliv.po_id}")
            if deliv.received_by_user_id not in req_ids:
                self.result.record_fail("FK_DELIVERY_RECIPIENT", f"Delivery {deliv.delivery_id} references invalid user {deliv.received_by_user_id}")
        self.result.record_pass("FK_DELIVERY_RELATIONS")

    def validate_enums(self):
        """Verify enum integrity for all classified fields."""
        # Check a sample of values to guarantee no unrecognized string values
        valid_pr_statuses = {s.value for s in self.bundle.purchase_requests[0].status.__class__}
        for pr in self.bundle.purchase_requests:
            if pr.status.value not in valid_pr_statuses:
                self.result.record_fail("ENUM_PR_STATUS", f"Invalid PR status {pr.status.value}")
        self.result.record_pass("ENUM_PR_STATUS")

        valid_rfq_statuses = {s.value for s in self.bundle.rfqs[0].status.__class__}
        for r in self.bundle.rfqs:
            if r.status.value not in valid_rfq_statuses:
                self.result.record_fail("ENUM_RFQ_STATUS", f"Invalid RFQ status {r.status.value}")
        self.result.record_pass("ENUM_RFQ_STATUS")

        valid_po_statuses = {s.value for s in self.bundle.purchase_orders[0].status.__class__}
        for p in self.bundle.purchase_orders:
            if p.status.value not in valid_po_statuses:
                self.result.record_fail("ENUM_PO_STATUS", f"Invalid PO status {p.status.value}")
        self.result.record_pass("ENUM_PO_STATUS")

        valid_deliv_statuses = {s.value for s in self.bundle.deliveries[0].delivery_status.__class__}
        for d in self.bundle.deliveries:
            if d.delivery_status.value not in valid_deliv_statuses:
                self.result.record_fail("ENUM_DELIV_STATUS", f"Invalid delivery status {d.delivery_status.value}")
        self.result.record_pass("ENUM_DELIVERY_STATUS")

    def validate_chronology(self):
        """Verify lifecycle date order: PR request_date <= RFQ issue_date <= award_date <= PO po_date <= Delivery."""
        pr_by_id = {p.request_id: p for p in self.bundle.purchase_requests}
        rfq_by_id = {r.rfq_id: r for r in self.bundle.rfqs}
        po_by_id = {p.po_id: p for p in self.bundle.purchase_orders}

        # PR <= RFQ
        for rfq in self.bundle.rfqs:
            pr = pr_by_id[rfq.request_id]
            pr_dt = datetime.fromisoformat(pr.request_date)
            rfq_dt = datetime.fromisoformat(rfq.issue_date)
            if pr_dt > rfq_dt:
                self.result.record_fail("CHRONOLOGY_PR_RFQ", f"PR date {pr_dt} is after RFQ date {rfq_dt}")
        self.result.record_pass("CHRONOLOGY_PR_RFQ")

        # PO >= PR
        for po in self.bundle.purchase_orders:
            pr = pr_by_id[po.request_id]
            pr_dt = datetime.fromisoformat(pr.request_date).date()
            po_dt = datetime.fromisoformat(po.po_date).date()
            if pr_dt > po_dt:
                self.result.record_fail("CHRONOLOGY_PR_PO", f"PR date {pr_dt} is after PO date {po_dt}")
        self.result.record_pass("CHRONOLOGY_PR_PO")

        # Delivery >= PO
        for d in self.bundle.deliveries:
            po = po_by_id[d.po_id]
            po_dt = datetime.fromisoformat(po.po_date).date()
            deliv_dt = datetime.fromisoformat(d.delivery_date).date()
            if deliv_dt < po_dt:
                self.result.record_fail("CHRONOLOGY_PO_DELIVERY", f"Delivery date {deliv_dt} before PO date {po_dt}")
        self.result.record_pass("CHRONOLOGY_PO_DELIVERY")

    def validate_arithmetic_reconciliation(self):
        """Verify mathematical reconciliations across headers and lines."""
        # 1. PR total == sum(request_lines)
        pr_lines_sum: Dict[str, float] = {}
        for rl in self.bundle.request_lines:
            pr_lines_sum[rl.request_id] = round(pr_lines_sum.get(rl.request_id, 0.0) + rl.estimated_line_total, 2)

        for pr in self.bundle.purchase_requests:
            line_sum = pr_lines_sum.get(pr.request_id, 0.0)
            if abs(pr.total_estimated_amount - line_sum) > 0.02:
                self.result.record_fail(
                    "MATH_PR_LINE_SUM",
                    f"PR {pr.request_id} header ${pr.total_estimated_amount} != lines sum ${line_sum}"
                )
        self.result.record_pass("MATH_PR_LINE_SUM")

        # 2. Quote base == sum(quote_lines)
        q_lines_sum: Dict[str, float] = {}
        for ql in self.bundle.quote_lines:
            q_lines_sum[ql.quote_id] = round(q_lines_sum.get(ql.quote_id, 0.0) + ql.line_total, 2)

        for q in self.bundle.supplier_quotes:
            line_sum = q_lines_sum.get(q.quote_id, 0.0)
            if abs(q.base_amount - line_sum) > 0.02:
                self.result.record_fail(
                    "MATH_QUOTE_LINE_SUM",
                    f"Quote {q.quote_id} base ${q.base_amount} != lines sum ${line_sum}"
                )
        self.result.record_pass("MATH_QUOTE_LINE_SUM")

        # 3. PO total == sum(po_lines)
        po_lines_sum: Dict[str, float] = {}
        for pl in self.bundle.po_lines:
            po_lines_sum[pl.po_id] = round(po_lines_sum.get(pl.po_id, 0.0) + pl.line_amount, 2)

        for po in self.bundle.purchase_orders:
            line_sum = po_lines_sum.get(po.po_id, 0.0)
            if abs(po.total_po_amount - line_sum) > 0.02:
                self.result.record_fail(
                    "MATH_PO_LINE_SUM",
                    f"PO {po.po_id} total ${po.total_po_amount} != lines sum ${line_sum}"
                )
        self.result.record_pass("MATH_PO_LINE_SUM")

    def validate_lifecycle_states(self):
        """Verify lifecycle consistency (e.g. FULFILLED PO has deliveries)."""
        deliveries_by_po: Dict[str, List] = {}
        for d in self.bundle.deliveries:
            deliveries_by_po.setdefault(d.po_id, []).append(d)

        for po in self.bundle.purchase_orders:
            if po.status.value == "FULFILLED":
                delivs = deliveries_by_po.get(po.po_id, [])
                if not delivs:
                    self.result.record_fail("LIFECYCLE_PO_FULFILLED", f"PO {po.po_id} is marked FULFILLED but has 0 deliveries")
        self.result.record_pass("LIFECYCLE_PO_DELIVERIES")

    def validate_audit_engine_accuracy(self):
        """Runs the independent ProcurementAuditor and tests precision/recall against ground truth."""
        auditor = ProcurementAuditor(
            departments=self.bundle.departments,
            budgets=self.bundle.budgets,
            requesters=self.bundle.requesters,
            suppliers=self.bundle.suppliers,
            requests=self.bundle.purchase_requests,
            request_lines=self.bundle.request_lines,
            rfqs=self.bundle.rfqs,
            quotes=self.bundle.supplier_quotes,
            approvals=self.bundle.approvals,
            pos=self.bundle.purchase_orders,
            po_lines=self.bundle.po_lines,
            deliveries=self.bundle.deliveries,
        )

        findings = auditor.scan_all()
        eval_metrics = auditor.evaluate_against_ground_truth(self.bundle.ground_truth)
        self.result.metrics["audit_engine_evaluation"] = eval_metrics

        # Precision & Recall should both be >= 0.90
        prec = eval_metrics["overall_precision"]
        rec = eval_metrics["overall_recall"]
        f1 = eval_metrics["overall_f1_score"]

        if prec >= 0.90 and rec >= 0.90:
            self.result.record_pass(f"AUDIT_EVAL_F1_SCORE_{f1:.2f}")
        else:
            self.result.record_warning(
                "AUDIT_EVAL_ACCURACY",
                f"Audit detection accuracy: Precision={prec:.2f}, Recall={rec:.2f}, F1={f1:.2f}",
            )

