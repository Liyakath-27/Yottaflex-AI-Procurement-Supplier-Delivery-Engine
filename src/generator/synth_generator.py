"""
End-to-End Synthetic Data Generator for Procurement & Supplier Delivery.
Implements Steps 1 through 7 of the synthetic data generation instructions.
"""
from typing import List, Dict, Any, Tuple, Optional
import random
from datetime import datetime, timedelta
import hashlib

from src.models.enums import (
    DepartmentCategory,
    BudgetStatus,
    ItemCategory,
    RequesterRole,
    Currency,
    PaymentTerms,
    SupplierRiskLevel,
    PurchaseRequestStatus,
    PriorityLevel,
    ProcurementMethod,
    ApprovalTier,
    ApprovalDecision,
    RFQStatus,
    QuoteStatus,
    PurchaseOrderStatus,
    DeliveryStatus,
    InspectionStatus,
    Carrier,
    AnomalyType,
    AnomalySeverity,
)
from src.models.entities import (
    Department,
    Budget,
    Requester,
    Supplier,
    PurchaseRequest,
    RequestLine,
    RFQ,
    SupplierQuote,
    QuoteLine,
    Approval,
    PurchaseOrder,
    POLine,
    Delivery,
    AuditEvent,
    GroundTruthAnomaly,
)
from src.generator.seed_data import (
    DEPARTMENTS_DATA,
    FIRST_NAMES,
    LAST_NAMES,
    ITEM_CATALOG,
    DELIVERY_DESTINATIONS,
)
from src.generator.anomaly_injector import AnomalyInjector
from src.engine.approval_matrix import get_required_tier, select_eligible_approver
from src.engine.quote_comparator import (
    calculate_landed_cost,
    rank_and_score_quotes,
    generate_award_rationale,
)
from src.engine.budget_tracker import BudgetTracker


class ProcurementDataBundle:
    def __init__(self):
        self.departments: List[Department] = []
        self.budgets: List[Budget] = []
        self.requesters: List[Requester] = []
        self.suppliers: List[Supplier] = []
        self.purchase_requests: List[PurchaseRequest] = []
        self.request_lines: List[RequestLine] = []
        self.rfqs: List[RFQ] = []
        self.supplier_quotes: List[SupplierQuote] = []
        self.quote_lines: List[QuoteLine] = []
        self.approvals: List[Approval] = []
        self.purchase_orders: List[PurchaseOrder] = []
        self.po_lines: List[POLine] = []
        self.deliveries: List[Delivery] = []
        self.audit_events: List[AuditEvent] = []
        self.ground_truth: List[GroundTruthAnomaly] = []


class SyntheticProcurementGenerator:
    def __init__(self, seed: int = 20261022, scale: str = "full"):
        self.seed = seed
        self.scale = scale
        self.rng = random.Random(seed)
        self.audit_counter = 1

        # Scale targets
        if scale == "starter":
            self.target_requesters = 30
            self.target_suppliers = 15
            self.target_requests = 120
            self.target_rfqs = 50
            self.target_quotes = 150
            self.target_pos = 90
        else:  # full
            self.target_requesters = 300
            self.target_suppliers = 120
            self.target_requests = 1200
            self.target_rfqs = 500
            self.target_quotes = 1500
            self.target_pos = 900

        self.bundle = ProcurementDataBundle()

    def _next_event_id(self) -> str:
        eid = f"EVT-{self.audit_counter:08d}"
        self.audit_counter += 1
        return eid

    def log_event(
        self,
        entity_type: str,
        entity_id: str,
        timestamp: str,
        actor_id: str,
        prev_state: Optional[str],
        new_state: str,
        action: str,
        details: str,
    ):
        """Append an immutable audit event."""
        self.bundle.audit_events.append(
            AuditEvent(
                event_id=self._next_event_id(),
                entity_type=entity_type,
                entity_id=entity_id,
                event_timestamp=timestamp,
                actor_id=actor_id,
                previous_state=prev_state,
                new_state=new_state,
                action_type=action,
                details=details,
            )
        )

    def generate_all(self) -> ProcurementDataBundle:
        """Run complete generation pipeline in strict dependency order."""
        # 1. Master Data
        self._generate_departments()
        self._generate_requesters()
        self._assign_department_heads()
        self._generate_budgets()
        self._generate_suppliers()

        # 2. Transactional Requests & Lines
        self._generate_purchase_requests()

        # 3. Approvals for Requests
        self._process_request_approvals()

        # 4. Sourcing & RFQs
        self._generate_rfqs_and_quotes()

        # 5. Purchase Orders & PO Lines
        self._generate_purchase_orders()

        # 6. Deliveries & Inbound Shipments
        self._generate_deliveries()

        # 7. Reconcile Budgets & Derived Metrics
        self._reconcile_budgets()

        # 8. Inject Labelled Edge Cases & Output Ground Truth
        self._inject_anomalies()

        return self.bundle

    def _generate_departments(self):
        for dept_id, name, cat, cc in DEPARTMENTS_DATA:
            dept = Department(
                department_id=dept_id,
                department_name=name,
                category=cat,
                cost_center_code=cc,
                head_requester_id=None,
                is_active=True,
            )
            self.bundle.departments.append(dept)

    def _generate_requesters(self):
        roles_pool = [
            (RequesterRole.JUNIOR_ANALYST, 0.0, 0.25),
            (RequesterRole.STAFF_SPECIALIST, 1000.0, 0.30),
            (RequesterRole.SENIOR_ENGINEER, 5000.0, 0.20),
            (RequesterRole.TEAM_LEAD, 10000.0, 0.12),
            (RequesterRole.DEPARTMENT_MANAGER, 50000.0, 0.08),
            (RequesterRole.DIRECTOR, 150000.0, 0.035),
            (RequesterRole.VP, 500000.0, 0.015),
        ]

        roles, limits, weights = zip(*roles_pool)

        base_date = datetime(2025, 1, 15, 9, 0, 0)
        dept_ids = [d.department_id for d in self.bundle.departments]

        for i in range(1, self.target_requesters + 1):
            req_id = f"REQ-{i:04d}"
            fn = self.rng.choice(FIRST_NAMES)
            ln = self.rng.choice(LAST_NAMES)
            email = f"{fn.lower()}.{ln.lower()}{i}@yottaflex.ai"
            # Ensure every department gets at least one employee
            if i <= len(dept_ids):
                dept_id = dept_ids[i - 1]
            else:
                dept_id = self.rng.choice(dept_ids)
            role_choice = self.rng.choices(roles, weights=weights, k=1)[0]
            role_idx = roles.index(role_choice)
            approval_limit = limits[role_idx]

            created_dt = base_date + timedelta(days=self.rng.randint(0, 300), hours=self.rng.randint(1, 8))

            requester = Requester(
                requester_id=req_id,
                name=f"{fn} {ln}",
                email=email,
                department_id=dept_id,
                role=role_choice,
                approval_limit=approval_limit,
                is_active=True,
                created_at=created_dt.isoformat(),
            )
            self.bundle.requesters.append(requester)

    def _assign_department_heads(self):
        """Ensure each department has a Department Head assigned."""
        dept_map = {d.department_id: d for d in self.bundle.departments}
        for d in self.bundle.departments:
            candidates = [
                r for r in self.bundle.requesters
                if r.department_id == d.department_id and r.approval_limit >= 10000.0
            ]
            if candidates:
                d.head_requester_id = candidates[0].requester_id
            else:
                dept_reqs = [r for r in self.bundle.requesters if r.department_id == d.department_id]
                if dept_reqs:
                    first_r = dept_reqs[0]
                    first_r.role = RequesterRole.DEPARTMENT_MANAGER
                    first_r.approval_limit = 50000.0
                    d.head_requester_id = first_r.requester_id

    def _generate_budgets(self):
        """Generate annual budgets for each department across relevant categories."""
        budget_idx = 1
        all_categories = list(ItemCategory)

        for dept in self.bundle.departments:
            # Each department gets 3 to 5 categorical budgets
            sample_cats = self.rng.sample(all_categories, k=self.rng.randint(3, 5))
            for cat in sample_cats:
                bid = f"BUD-2026-{budget_idx:03d}"
                budget_idx += 1
                # Budget amounts scale realistically: $2.5M - $6.0M
                allocated = round(self.rng.uniform(2500000.0, 6000000.0), -3)
                budget = Budget(
                    budget_id=bid,
                    department_id=dept.department_id,
                    fiscal_year=2026,
                    category=cat,
                    allocated_amount=allocated,
                    committed_amount=0.0,
                    spent_amount=0.0,
                    remaining_balance=allocated,
                    start_date="2026-01-01",
                    end_date="2026-12-31",
                    status=BudgetStatus.ACTIVE,
                )
                self.bundle.budgets.append(budget)

    def _generate_suppliers(self):
        """Generate suppliers with realistic ratings, categories, codes, and risk profiles."""
        supplier_prefixes = [
            ("APEX", "Apex Technologies"), ("DELL", "Dell Enterprise Solutions"),
            ("LOGI", "LogiGlobal Freight"), ("FAST", "FastTrack Sourcing"),
            ("ACME", "Acme Industrial Supply"), ("TECH", "TechPro Components"),
            ("GLBL", "Global Warehousing Corp"), ("PRME", "Prime Cloud Services"),
            ("NEXT", "NextGen Microchips"), ("VITA", "Vital Corporate Furnishings"),
            ("OMNI", "OmniNetwork Solutions"), ("CORE", "CoreLogic Security"),
            ("VALU", "ValueFleet Logistics"), ("NEXS", "Nexus Professional Services"),
            ("SYNR", "Synergy Workspace Products"), ("TRUE", "TrueSource Electronics"),
            ("AERO", "AeroExpress Cargo"), ("BEAC", "Beacon Strategic Advisory"),
            ("DATA", "DataVault Analytics"), ("FLEX", "FlexiStaffing Partners"),
            ("SUMM", "Summit Precision Labs"), ("CSTN", "Capstone Engineering"),
            ("VELO", "Velocity Systems"), ("PNTM", "PointMark Compliance"),
            ("INNO", "Innovate Office Systems"), ("QUAL", "QualiTech Supplies"),
        ]

        cats = list(ItemCategory)
        currencies = [Currency.USD, Currency.USD, Currency.USD, Currency.EUR, Currency.GBP]
        pay_terms = [PaymentTerms.NET_30, PaymentTerms.NET_45, PaymentTerms.NET_60, PaymentTerms.NET_15]

        base_date = datetime(2025, 3, 1, 10, 0, 0)

        for i in range(1, self.target_suppliers + 1):
            sid = f"SUP-{i:03d}"
            prefix, base_name = supplier_prefixes[(i - 1) % len(supplier_prefixes)]
            code = f"{prefix}{i:02d}"
            name = f"{base_name} #{i}"
            category = cats[(i - 1) % len(cats)]

            rating = round(self.rng.uniform(3.2, 5.0), 2)
            on_time = round(self.rng.uniform(0.82, 0.99), 3)
            quality = round(self.rng.uniform(0.88, 0.99), 3)

            risk = SupplierRiskLevel.LOW
            if rating < 3.8 or on_time < 0.88:
                risk = SupplierRiskLevel.MEDIUM
            if rating < 3.4 or on_time < 0.85:
                risk = SupplierRiskLevel.HIGH

            created_dt = base_date + timedelta(days=self.rng.randint(0, 250))

            supplier = Supplier(
                supplier_id=sid,
                supplier_code=code,
                name=name,
                category=category,
                contact_email=f"procurement@{code.lower()}.com",
                currency=self.rng.choice(currencies),
                payment_terms=self.rng.choice(pay_terms),
                performance_rating=rating,
                risk_level=risk,
                is_active=True,
                on_time_delivery_rate=on_time,
                quality_score=quality,
                created_at=created_dt.isoformat(),
            )
            self.bundle.suppliers.append(supplier)

    def _generate_purchase_requests(self):
        """Generate purchase requests and request lines with realistic business distributions."""
        start_date = datetime(2026, 1, 2, 8, 30, 0)
        requesters = self.bundle.requesters
        budgets_by_dept_cat: Dict[Tuple[str, ItemCategory], Budget] = {
            (b.department_id, b.category): b for b in self.bundle.budgets
        }

        line_counter = 1
        for i in range(1, self.target_requests + 1):
            pr_id = f"PR-2026-{i:06d}"
            requester = self.rng.choice(requesters)
            dept_id = requester.department_id

            # Find valid budget in dept
            dept_budgets = [b for b in self.bundle.budgets if b.department_id == dept_id]
            if not dept_budgets:
                chosen_budget = self.rng.choice(self.bundle.budgets)
                dept_id = chosen_budget.department_id
            else:
                chosen_budget = self.rng.choice(dept_budgets)

            category = chosen_budget.category
            items = ITEM_CATALOG.get(category, ITEM_CATALOG[ItemCategory.OFFICE_SUPPLIES])

            # Generation date distributed throughout 2026
            day_offset = int((i / self.target_requests) * 280) + self.rng.randint(0, 5)
            req_dt = start_date + timedelta(days=day_offset, hours=self.rng.randint(1, 9))
            required_dt = req_dt + timedelta(days=self.rng.randint(14, 45))

            # 1 to 4 request lines
            num_lines = self.rng.choices([1, 2, 3, 4], weights=[0.4, 0.35, 0.15, 0.1], k=1)[0]
            sampled_items = self.rng.sample(items, min(num_lines, len(items)))

            lines_total = 0.0
            for l_idx, (desc, uom, base_price) in enumerate(sampled_items, start=1):
                lid = f"{pr_id}-L{l_idx:02d}"
                qty = self.rng.choices([1, 2, 5, 10, 20, 50], weights=[0.35, 0.25, 0.2, 0.1, 0.07, 0.03], k=1)[0]
                price = round(base_price * self.rng.uniform(0.95, 1.05), 2)
                line_total = round(qty * price, 2)
                lines_total += line_total

                req_line = RequestLine(
                    line_id=lid,
                    request_id=pr_id,
                    line_number=l_idx,
                    item_description=desc,
                    item_category=category,
                    quantity=qty,
                    unit_of_measure=uom,
                    estimated_unit_price=price,
                    estimated_line_total=line_total,
                )
                self.bundle.request_lines.append(req_line)

            lines_total = round(lines_total, 2)
            tier = get_required_tier(lines_total)

            # Sourcing method
            is_single_source = False
            justification = None
            if lines_total < 2500.0 and self.rng.random() < 0.3:
                method = ProcurementMethod.CATALOG_DIRECT
            elif self.rng.random() < 0.08:  # 8% single-source exceptions
                method = ProcurementMethod.SINGLE_SOURCE
                is_single_source = True
                justification = f"Sole proprietary provider for {category.value} critical operational infrastructure."
            else:
                method = ProcurementMethod.COMPETITIVE_BID

            # Split purchase injection pattern (PRs around $950 - $990)
            is_split = False
            if 900.0 <= lines_total <= 995.0 and self.rng.random() < 0.15:
                is_split = True

            pr = PurchaseRequest(
                request_id=pr_id,
                requester_id=requester.requester_id,
                department_id=dept_id,
                budget_id=chosen_budget.budget_id,
                request_date=req_dt.isoformat(),
                required_date=required_dt.isoformat(),
                status=PurchaseRequestStatus.SUBMITTED,
                category=category,
                priority=self.rng.choices(
                    [PriorityLevel.LOW, PriorityLevel.MEDIUM, PriorityLevel.HIGH, PriorityLevel.URGENT],
                    weights=[0.15, 0.55, 0.22, 0.08],
                    k=1
                )[0],
                total_estimated_amount=lines_total,
                currency=Currency.USD,
                procurement_method=method,
                single_source_justification=justification,
                is_split_purchase=is_split,
                approval_tier_required=tier,
            )
            self.bundle.purchase_requests.append(pr)

            self.log_event(
                entity_type="PURCHASE_REQUEST",
                entity_id=pr_id,
                timestamp=req_dt.isoformat(),
                actor_id=requester.requester_id,
                prev_state=None,
                new_state=PurchaseRequestStatus.SUBMITTED.value,
                action="REQUEST_SUBMITTED",
                details=f"Submitted purchase request for {category.value} totaling ${lines_total:,.2f}",
            )

    def _process_request_approvals(self):
        """Execute multi-tier approvals according to approval thresholds."""
        app_counter = 1
        for pr in self.bundle.purchase_requests:
            req_dt = datetime.fromisoformat(pr.request_date)
            decision_dt = req_dt + timedelta(hours=self.rng.randint(2, 48))

            approver = select_eligible_approver(
                tier=pr.approval_tier_required,
                department_id=pr.department_id,
                requesters=self.bundle.requesters,
                pr_requester_id=pr.requester_id,
            )

            # Fallback if no specific approver found
            if not approver:
                approver = [r for r in self.bundle.requesters if r.approval_limit >= 150000.0][0]

            # 92% approval rate, 8% rejection
            is_approved = self.rng.random() < 0.92
            decision = ApprovalDecision.APPROVED if is_approved else ApprovalDecision.REJECTED
            comments = "Approved within authorized department budget allocation." if is_approved else "Rejected: item redundant or budget constraint."

            aid = f"APP-2026-{app_counter:06d}"
            app_counter += 1

            approval = Approval(
                approval_id=aid,
                entity_type="PURCHASE_REQUEST",
                entity_id=pr.request_id,
                tier_level=pr.approval_tier_required,
                approver_id=approver.requester_id,
                decision=decision,
                decision_date=decision_dt.isoformat(),
                amount_evaluated=pr.total_estimated_amount,
                approver_limit_at_decision=approver.approval_limit,
                comments=comments,
                is_override=False,
            )
            self.bundle.approvals.append(approval)

            new_status = PurchaseRequestStatus.APPROVED if is_approved else PurchaseRequestStatus.REJECTED
            pr.status = new_status

            self.log_event(
                entity_type="PURCHASE_REQUEST",
                entity_id=pr.request_id,
                timestamp=decision_dt.isoformat(),
                actor_id=approver.requester_id,
                prev_state=PurchaseRequestStatus.SUBMITTED.value,
                new_state=new_status.value,
                action="APPROVAL_DECISION",
                details=f"Decision {decision.value} by {approver.name} ({approver.role.value}) for ${pr.total_estimated_amount:,.2f}",
            )

    def _generate_rfqs_and_quotes(self):
        """Create RFQs for approved competitive requests, solicit >=3 quotes, score and award."""
        approved_prs = [
            pr for pr in self.bundle.purchase_requests
            if pr.status == PurchaseRequestStatus.APPROVED
            and pr.procurement_method == ProcurementMethod.COMPETITIVE_BID
        ]

        # Limit to target_rfqs
        eligible_prs = approved_prs[:self.target_rfqs]

        suppliers_by_cat: Dict[ItemCategory, List[Supplier]] = {}
        for s in self.bundle.suppliers:
            suppliers_by_cat.setdefault(s.category, []).append(s)

        suppliers_by_id = {s.supplier_id: s for s in self.bundle.suppliers}
        req_lines_by_pr: Dict[str, List[RequestLine]] = {}
        for rl in self.bundle.request_lines:
            req_lines_by_pr.setdefault(rl.request_id, []).append(rl)

        rfq_counter = 1
        quote_counter = 1
        quote_line_counter = 1

        for pr in eligible_prs:
            rfq_id = f"RFQ-2026-{rfq_counter:06d}"
            rfq_counter += 1

            pr_dt = datetime.fromisoformat(pr.request_date)
            rfq_issue_dt = pr_dt + timedelta(days=self.rng.randint(1, 3))
            rfq_deadline = rfq_issue_dt + timedelta(days=14)

            rfq = RFQ(
                rfq_id=rfq_id,
                request_id=pr.request_id,
                issue_date=rfq_issue_dt.isoformat(),
                submission_deadline=rfq_deadline.isoformat(),
                status=RFQStatus.OPEN,
                target_currency=Currency.USD,
                min_quotes_required=3,
                quotes_received_count=0,
                award_date=None,
                awarded_supplier_id=None,
                awarded_quote_id=None,
            )
            self.bundle.rfqs.append(rfq)
            pr.status = PurchaseRequestStatus.IN_SOURCING

            # Select at least 3 suppliers in the category (or fallback)
            matching_suppliers = suppliers_by_cat.get(pr.category, self.bundle.suppliers)
            if len(matching_suppliers) < 3:
                matching_suppliers = self.bundle.suppliers
            selected_suppliers = self.rng.sample(matching_suppliers, min(3, len(matching_suppliers)))

            # Capture quotes
            rfq_quotes: List[SupplierQuote] = []
            lines = req_lines_by_pr.get(pr.request_id, [])

            for supp in selected_suppliers:
                supp_code = supp.supplier_code.split("#")[0].strip()
                qid = f"QUO-{supp_code}-2026-{quote_counter:06d}"
                quote_counter += 1

                quote_dt = rfq_issue_dt + timedelta(days=self.rng.randint(3, 10))
                validity_end = quote_dt + timedelta(days=self.rng.randint(30, 60))

                # FX rate
                fx = 1.0
                if supp.currency == Currency.EUR:
                    fx = 1.08
                elif supp.currency == Currency.GBP:
                    fx = 1.28
                elif supp.currency == Currency.CAD:
                    fx = 0.74

                # Generate quote lines based on PR lines
                quote_base = 0.0
                for line in lines:
                    qlid = f"{qid}-L{line.line_number:02d}"
                    unit_var = self.rng.uniform(0.90, 1.15)
                    q_unit_price = round(line.estimated_unit_price * unit_var / fx, 2)
                    q_line_total = round(line.quantity * q_unit_price, 2)
                    quote_base += q_line_total

                    quote_line = QuoteLine(
                        quote_line_id=qlid,
                        quote_id=qid,
                        line_number=line.line_number,
                        item_description=line.item_description,
                        quantity=line.quantity,
                        unit_price=q_unit_price,
                        line_total=q_line_total,
                    )
                    self.bundle.quote_lines.append(quote_line)

                # Cost components
                freight = round(self.rng.uniform(50.0, 350.0), 2) if pr.category in [ItemCategory.HARDWARE, ItemCategory.FACILITIES, ItemCategory.OFFICE_SUPPLIES] else 0.0
                duty = round(quote_base * 0.03, 2) if supp.currency != Currency.USD else 0.0
                discount = round(quote_base * 0.05, 2) if self.rng.random() < 0.4 else 0.0

                landed_cost_usd = calculate_landed_cost(
                    base_amount=quote_base,
                    discount_amount=discount,
                    freight_cost=freight,
                    tax_duty_amount=duty,
                    exchange_rate_to_usd=fx,
                )

                lead_time = self.rng.randint(5, 28)

                quote = SupplierQuote(
                    quote_id=qid,
                    rfq_id=rfq_id,
                    supplier_id=supp.supplier_id,
                    quote_date=quote_dt.strftime("%Y-%m-%d"),
                    validity_end_date=validity_end.strftime("%Y-%m-%d"),
                    currency=supp.currency,
                    exchange_rate_to_usd=fx,
                    base_amount=round(quote_base, 2),
                    freight_cost=freight,
                    tax_duty_amount=duty,
                    discount_amount=discount,
                    total_landed_cost_usd=landed_cost_usd,
                    promised_lead_time_days=lead_time,
                    payment_terms=supp.payment_terms,
                    warranty_months=12,
                    quote_status=QuoteStatus.SUBMITTED,
                    landed_cost_rank=1,
                    selection_score=0.0,
                    award_rationale=None,
                )
                rfq_quotes.append(quote)
                self.bundle.supplier_quotes.append(quote)

            rfq.quotes_received_count = len(rfq_quotes)

            # Score and rank quotes
            scored_quotes = rank_and_score_quotes(rfq_quotes, suppliers_by_id)

            # Award to highest selection score (or lowest cost)
            awarded = max(scored_quotes, key=lambda q: q.selection_score)
            cheapest = sorted(scored_quotes, key=lambda q: q.total_landed_cost_usd)[0]
            awarded_supplier = suppliers_by_id[awarded.supplier_id]

            award_dt = rfq_deadline + timedelta(days=self.rng.randint(1, 3))
            rfq.award_date = award_dt.strftime("%Y-%m-%d")
            rfq.awarded_supplier_id = awarded.supplier_id
            rfq.awarded_quote_id = awarded.quote_id
            rfq.status = RFQStatus.AWARDED

            for q in scored_quotes:
                if q.quote_id == awarded.quote_id:
                    q.quote_status = QuoteStatus.ACCEPTED
                    q.award_rationale = generate_award_rationale(q, cheapest, awarded_supplier)
                else:
                    q.quote_status = QuoteStatus.REJECTED

            self.log_event(
                entity_type="RFQ",
                entity_id=rfq_id,
                timestamp=award_dt.isoformat(),
                actor_id=pr.requester_id,
                prev_state=RFQStatus.OPEN.value,
                new_state=RFQStatus.AWARDED.value,
                action="AWARD_SUPPLIER",
                details=f"Awarded to {awarded_supplier.name} via quote {awarded.quote_id} (${awarded.total_landed_cost_usd:,.2f})",
            )

    def _generate_purchase_orders(self):
        """Generate Purchase Orders and PO lines from awarded quotes or approved direct/single-source requests."""
        po_counter = 1
        quote_by_id = {q.quote_id: q for q in self.bundle.supplier_quotes}
        quote_lines_by_quote: Dict[str, List[QuoteLine]] = {}
        for ql in self.bundle.quote_lines:
            quote_lines_by_quote.setdefault(ql.quote_id, []).append(ql)

        approvals_by_pr = {a.entity_id: a for a in self.bundle.approvals if a.decision == ApprovalDecision.APPROVED}
        req_lines_by_pr: Dict[str, List[RequestLine]] = {}
        for rl in self.bundle.request_lines:
            req_lines_by_pr.setdefault(rl.request_id, []).append(rl)

        # 1. POs from Awarded RFQs
        awarded_rfqs = [r for r in self.bundle.rfqs if r.status == RFQStatus.AWARDED]
        pr_by_id = {p.request_id: p for p in self.bundle.purchase_requests}

        for rfq in awarded_rfqs:
            if po_counter > self.target_pos:
                break

            pr = pr_by_id.get(rfq.request_id)
            if not pr:
                continue

            quote = quote_by_id.get(rfq.awarded_quote_id)
            if not quote:
                continue

            po_id = f"PO-2026-{po_counter:06d}"
            po_counter += 1

            award_dt = datetime.fromisoformat(rfq.award_date) if rfq.award_date else datetime(2026, 3, 1)
            po_dt = award_dt + timedelta(days=1)
            req_deliv_dt = po_dt + timedelta(days=quote.promised_lead_time_days)

            # Generate PO lines matching awarded quote lines exactly
            qlines = quote_lines_by_quote.get(quote.quote_id, [])
            po_total = 0.0

            for ql in qlines:
                poline_id = f"{po_id}-L{ql.line_number:02d}"
                # Convert unit price to USD
                usd_unit_price = round(ql.unit_price * quote.exchange_rate_to_usd, 2)
                line_amt = round(ql.quantity * usd_unit_price, 2)
                po_total += line_amt

                po_line = POLine(
                    po_line_id=poline_id,
                    po_id=po_id,
                    line_number=ql.line_number,
                    item_description=ql.item_description,
                    quantity_ordered=ql.quantity,
                    unit_price=usd_unit_price,
                    line_amount=line_amt,
                    quantity_received=0,
                )
                self.bundle.po_lines.append(po_line)

            po_total = round(po_total, 2)
            approval = approvals_by_pr.get(pr.request_id)

            po = PurchaseOrder(
                po_id=po_id,
                request_id=pr.request_id,
                rfq_id=rfq.rfq_id,
                quote_id=quote.quote_id,
                supplier_id=quote.supplier_id,
                po_date=po_dt.strftime("%Y-%m-%d"),
                required_delivery_date=req_deliv_dt.strftime("%Y-%m-%d"),
                status=PurchaseOrderStatus.ISSUED,
                currency=Currency.USD,
                total_po_amount=po_total,
                payment_terms=quote.payment_terms,
                delivery_address=self.rng.choice(DELIVERY_DESTINATIONS),
                approval_reference_id=approval.approval_id if approval else None,
            )
            self.bundle.purchase_orders.append(po)
            pr.status = PurchaseRequestStatus.PO_CREATED

            self.log_event(
                entity_type="PURCHASE_ORDER",
                entity_id=po_id,
                timestamp=po_dt.isoformat(),
                actor_id=pr.requester_id,
                prev_state=None,
                new_state=PurchaseOrderStatus.ISSUED.value,
                action="PO_ISSUED",
                details=f"Issued PO {po_id} to supplier {quote.supplier_id} for ${po_total:,.2f}",
            )

        # 2. Additional POs for single-source / catalog PRs to reach target_pos
        remaining_prs = [
            pr for pr in self.bundle.purchase_requests
            if pr.status == PurchaseRequestStatus.APPROVED
            and pr.request_id not in [p.request_id for p in self.bundle.purchase_orders]
        ]

        for pr in remaining_prs:
            if po_counter > self.target_pos:
                break

            po_id = f"PO-2026-{po_counter:06d}"
            po_counter += 1

            # Match or pick supplier in category
            cat_suppliers = [s for s in self.bundle.suppliers if s.category == pr.category]
            supp = self.rng.choice(cat_suppliers) if cat_suppliers else self.rng.choice(self.bundle.suppliers)

            pr_dt = datetime.fromisoformat(pr.request_date)
            po_dt = pr_dt + timedelta(days=2)
            req_deliv_dt = po_dt + timedelta(days=self.rng.randint(7, 21))

            lines = req_lines_by_pr.get(pr.request_id, [])
            po_total = 0.0

            for rl in lines:
                poline_id = f"{po_id}-L{rl.line_number:02d}"
                po_total += rl.estimated_line_total

                po_line = POLine(
                    po_line_id=poline_id,
                    po_id=po_id,
                    line_number=rl.line_number,
                    item_description=rl.item_description,
                    quantity_ordered=rl.quantity,
                    unit_price=rl.estimated_unit_price,
                    line_amount=rl.estimated_line_total,
                    quantity_received=0,
                )
                self.bundle.po_lines.append(po_line)

            po_total = round(po_total, 2)
            approval = approvals_by_pr.get(pr.request_id)

            po = PurchaseOrder(
                po_id=po_id,
                request_id=pr.request_id,
                rfq_id=None,
                quote_id=None,
                supplier_id=supp.supplier_id,
                po_date=po_dt.strftime("%Y-%m-%d"),
                required_delivery_date=req_deliv_dt.strftime("%Y-%m-%d"),
                status=PurchaseOrderStatus.ISSUED,
                currency=Currency.USD,
                total_po_amount=po_total,
                payment_terms=supp.payment_terms,
                delivery_address=self.rng.choice(DELIVERY_DESTINATIONS),
                approval_reference_id=approval.approval_id if approval else None,
            )
            self.bundle.purchase_orders.append(po)
            pr.status = PurchaseRequestStatus.PO_CREATED

    def _generate_deliveries(self):
        """Generate delivery events, carrier shipments, tracking, partials, and quality inspections."""
        carriers = [Carrier.FEDEX, Carrier.UPS, Carrier.DHL, Carrier.FREIGHT_DIRECT, Carrier.MAERSK]
        requester_ids = [r.requester_id for r in self.bundle.requesters]
        po_lines_by_po: Dict[str, List[POLine]] = {}
        for pol in self.bundle.po_lines:
            po_lines_by_po.setdefault(pol.po_id, []).append(pol)

        for po in self.bundle.purchase_orders:
            po_dt = datetime.fromisoformat(po.po_date)
            req_deliv_dt = datetime.fromisoformat(po.required_delivery_date)
            lines = po_lines_by_po.get(po.po_id, [])
            total_items_ordered = sum(l.quantity_ordered for l in lines)

            # Delivery scenario:
            # 80% On-time complete delivery
            # 12% Late delivery
            # 6% Partial delivery (two shipments)
            # 2% Damaged / Inspection concession
            rand_val = self.rng.random()

            if rand_val < 0.80:  # On time complete
                actual_days = self.rng.randint(2, max(3, (req_deliv_dt - po_dt).days))
                deliv_dt = po_dt + timedelta(days=actual_days)
                status = DeliveryStatus.DELIVERED_ON_TIME
                insp = InspectionStatus.PASSED

                for l in lines:
                    l.quantity_received = l.quantity_ordered

                deliv_id = f"DEL-{po.po_id}-01"
                carrier = self.rng.choice(carriers)
                tracking = f"{carrier.value[:3]}-{self.rng.randint(10000000, 99999999)}"

                delivery = Delivery(
                    delivery_id=deliv_id,
                    po_id=po.po_id,
                    shipment_number=1,
                    delivery_date=deliv_dt.strftime("%Y-%m-%d"),
                    carrier=carrier,
                    tracking_number=tracking,
                    delivery_status=status,
                    received_by_user_id=self.rng.choice(requester_ids),
                    inspection_status=insp,
                    items_delivered_count=total_items_ordered,
                    is_partial=False,
                    notes="Delivered in full, all line items inspected and verified.",
                )
                self.bundle.deliveries.append(delivery)
                po.status = PurchaseOrderStatus.FULFILLED

            elif rand_val < 0.92:  # Late delivery
                late_days = self.rng.randint(3, 14)
                deliv_dt = req_deliv_dt + timedelta(days=late_days)
                status = DeliveryStatus.DELIVERED_LATE
                insp = InspectionStatus.PASSED

                for l in lines:
                    l.quantity_received = l.quantity_ordered

                deliv_id = f"DEL-{po.po_id}-01"
                carrier = self.rng.choice(carriers)
                tracking = f"{carrier.value[:3]}-{self.rng.randint(10000000, 99999999)}"

                delivery = Delivery(
                    delivery_id=deliv_id,
                    po_id=po.po_id,
                    shipment_number=1,
                    delivery_date=deliv_dt.strftime("%Y-%m-%d"),
                    carrier=carrier,
                    tracking_number=tracking,
                    delivery_status=status,
                    received_by_user_id=self.rng.choice(requester_ids),
                    inspection_status=insp,
                    items_delivered_count=total_items_ordered,
                    is_partial=False,
                    notes=f"Carrier transit delay ({late_days} days overdue). Accepted upon arrival.",
                )
                self.bundle.deliveries.append(delivery)
                po.status = PurchaseOrderStatus.FULFILLED

            elif rand_val < 0.98:  # Partial delivery (2 shipments)
                # First shipment (60% of items)
                deliv1_dt = po_dt + timedelta(days=self.rng.randint(3, 10))
                carrier1 = self.rng.choice(carriers)
                track1 = f"{carrier1.value[:3]}-{self.rng.randint(10000000, 99999999)}"
                items_p1 = max(1, int(total_items_ordered * 0.6))
                items_p2 = total_items_ordered - items_p1

                deliv1 = Delivery(
                    delivery_id=f"DEL-{po.po_id}-01",
                    po_id=po.po_id,
                    shipment_number=1,
                    delivery_date=deliv1_dt.strftime("%Y-%m-%d"),
                    carrier=carrier1,
                    tracking_number=track1,
                    delivery_status=DeliveryStatus.IN_TRANSIT,
                    received_by_user_id=self.rng.choice(requester_ids),
                    inspection_status=InspectionStatus.PASSED,
                    items_delivered_count=items_p1,
                    is_partial=True,
                    notes=f"First partial batch received ({items_p1}/{total_items_ordered} items).",
                )
                self.bundle.deliveries.append(deliv1)

                # Second shipment
                deliv2_dt = deliv1_dt + timedelta(days=self.rng.randint(5, 12))
                carrier2 = self.rng.choice(carriers)
                track2 = f"{carrier2.value[:3]}-{self.rng.randint(10000000, 99999999)}"

                deliv2 = Delivery(
                    delivery_id=f"DEL-{po.po_id}-02",
                    po_id=po.po_id,
                    shipment_number=2,
                    delivery_date=deliv2_dt.strftime("%Y-%m-%d"),
                    carrier=carrier2,
                    tracking_number=track2,
                    delivery_status=DeliveryStatus.DELIVERED_ON_TIME if deliv2_dt <= req_deliv_dt else DeliveryStatus.DELIVERED_LATE,
                    received_by_user_id=self.rng.choice(requester_ids),
                    inspection_status=InspectionStatus.PASSED,
                    items_delivered_count=items_p2,
                    is_partial=False,
                    notes=f"Final remainder batch received ({items_p2} items). Order complete.",
                )
                self.bundle.deliveries.append(deliv2)

                for l in lines:
                    l.quantity_received = l.quantity_ordered
                po.status = PurchaseOrderStatus.FULFILLED

            else:  # Quality concession or damaged
                deliv_dt = po_dt + timedelta(days=self.rng.randint(4, 12))
                carrier = self.rng.choice(carriers)
                track = f"{carrier.value[:3]}-{self.rng.randint(10000000, 99999999)}"

                for l in lines:
                    l.quantity_received = l.quantity_ordered

                delivery = Delivery(
                    delivery_id=f"DEL-{po.po_id}-01",
                    po_id=po.po_id,
                    shipment_number=1,
                    delivery_date=deliv_dt.strftime("%Y-%m-%d"),
                    carrier=carrier,
                    tracking_number=track,
                    delivery_status=DeliveryStatus.DAMAGED,
                    received_by_user_id=self.rng.choice(requester_ids),
                    inspection_status=InspectionStatus.ACCEPTED_WITH_CONCESSION,
                    items_delivered_count=total_items_ordered,
                    is_partial=False,
                    notes="Packaging dented; goods tested functional and accepted with 5% discount concession.",
                )
                self.bundle.deliveries.append(delivery)
                po.status = PurchaseOrderStatus.FULFILLED

            self.log_event(
                entity_type="DELIVERY",
                entity_id=f"DEL-{po.po_id}-01",
                timestamp=deliv_dt.isoformat(),
                actor_id="SYSTEM",
                prev_state=None,
                new_state=status.value,
                action="DELIVERY_RECORDED",
                details=f"Inbound shipment recorded for {po.po_id}: {status.value}",
            )

    def _reconcile_budgets(self):
        """Calculate committed and spent amounts directly from operational POs and PRs."""
        budget_map = {b.budget_id: b for b in self.bundle.budgets}
        pr_by_id = {p.request_id: p for p in self.bundle.purchase_requests}

        # Reset counters
        for b in budget_map.values():
            b.committed_amount = 0.0
            b.spent_amount = 0.0

        # POs allocate spend or commitment
        for po in self.bundle.purchase_orders:
            pr = pr_by_id.get(po.request_id)
            if not pr:
                continue
            b = budget_map.get(pr.budget_id)
            if not b:
                continue

            if po.status == PurchaseOrderStatus.FULFILLED:
                b.spent_amount = round(b.spent_amount + po.total_po_amount, 2)
            else:
                b.committed_amount = round(b.committed_amount + po.total_po_amount, 2)

        # PRs approved but no PO yet
        pos_by_pr = {p.request_id for p in self.bundle.purchase_orders}
        for pr in self.bundle.purchase_requests:
            if pr.status == PurchaseRequestStatus.APPROVED and pr.request_id not in pos_by_pr:
                b = budget_map.get(pr.budget_id)
                if b:
                    b.committed_amount = round(b.committed_amount + pr.total_estimated_amount, 2)

        # Recalculate remaining balances
        tracker = BudgetTracker(budget_map)
        tracker.recalculate_all()

    def _inject_anomalies(self):
        """Inject edge cases and produce ground truth records."""
        injector = AnomalyInjector(self.rng)

        quotes_by_id = {q.quote_id: q for q in self.bundle.supplier_quotes}
        quotes_by_rfq: Dict[str, List[SupplierQuote]] = {}
        for q in self.bundle.supplier_quotes:
            quotes_by_rfq.setdefault(q.rfq_id, []).append(q)

        req_lines_by_pr: Dict[str, List[RequestLine]] = {}
        for rl in self.bundle.request_lines:
            req_lines_by_pr.setdefault(rl.request_id, []).append(rl)

        requests_by_budget: Dict[str, List[PurchaseRequest]] = {}
        for pr in self.bundle.purchase_requests:
            requests_by_budget.setdefault(pr.budget_id, []).append(pr)

        # 1. PO without approval
        injector.inject_po_without_approval(self.bundle.purchase_orders)

        # 2. Quote expired before award
        injector.inject_quote_expired_before_award(self.bundle.rfqs, quotes_by_id)

        # 3. Selected quote not cheapest without documented rationale
        injector.inject_non_cheapest_without_rationale(
            self.bundle.rfqs, quotes_by_rfq, quotes_by_id
        )

        # 4. Supplier inactive
        injector.inject_inactive_supplier(
            self.bundle.suppliers, self.bundle.purchase_orders, self.bundle.supplier_quotes
        )

        # 5. Budget overrun
        injector.inject_budget_overrun(self.bundle.budgets, requests_by_budget)

        # 6. Duplicate requests
        injector.inject_duplicate_requests(self.bundle.purchase_requests, req_lines_by_pr)

        # 7. Quote currency mismatch
        injector.inject_quote_currency_mismatch(self.bundle.supplier_quotes)

        # Synchronize back any additional request lines created by duplicates
        all_lines = []
        for lines_list in req_lines_by_pr.values():
            all_lines.extend(lines_list)
        self.bundle.request_lines = all_lines

        self.bundle.ground_truth = injector.ground_truth_records
