"""
Interactive End-to-End Workflow Simulator.
Simulates a live procurement transaction from request to delivery with full audit logging.
"""
import random
from datetime import datetime, timedelta
from src.models.enums import (
    DepartmentCategory, ItemCategory, RequesterRole, Currency, 
    PaymentTerms, PurchaseRequestStatus, PriorityLevel, ProcurementMethod,
    ApprovalTier, ApprovalDecision, RFQStatus, QuoteStatus,
    PurchaseOrderStatus, DeliveryStatus, InspectionStatus, Carrier
)
from src.engine.approval_matrix import get_required_tier
from src.engine.quote_comparator import calculate_landed_cost, rank_and_score_quotes, generate_award_rationale
from src.models.entities import Supplier


def run_simulation(
    item_name: str = "High-Performance AI Accelerator PCIe 80GB",
    quantity: int = 5,
    est_unit_price: float = 9500.0,
    dept_name: str = "Data Science & AI Research",
    requester_name: str = "Dr. Elena Vance (Staff Specialist)",
):
    print("=" * 70)
    print("    LIVE END-TO-END PROCUREMENT WORKFLOW SIMULATION")
    print("=" * 70)

    # 1. Purchase Request Creation
    total_amount = quantity * est_unit_price
    pr_id = "PR-2026-999001"
    req_date = datetime.now()
    req_deliv_date = req_date + timedelta(days=30)
    tier = get_required_tier(total_amount)

    print(f"\n[STEP 1: PURCHASE REQUEST CREATED]")
    print(f"  Request ID        : {pr_id}")
    print(f"  Originator        : {requester_name}")
    print(f"  Department        : {dept_name}")
    print(f"  Item Requested    : {quantity}x '{item_name}' @ ${est_unit_price:,.2f} each")
    print(f"  Total Estimated   : ${total_amount:,.2f}")
    print(f"  Approval Tier Req : {tier.value} (Threshold: >$10,000 Director Sign-off)")
    print(f"  Sourcing Method   : COMPETITIVE_BID (Mandates >=3 Supplier Quotes)")

    # 2. Approval Matrix Routing
    print(f"\n[STEP 2: MULTI-TIER APPROVAL ROUTING]")
    approver_name = "Marcus Zhao (Finance Director, Limit: $50,000)"
    approval_id = "APP-2026-999001"
    print(f"  Routed Approver   : {approver_name}")
    print(f"  Approval ID       : {approval_id}")
    print(f"  Decision          : APPROVED")
    print(f"  Audit Comments    : 'Approved under AI Infrastructure 2026 CapEx budget.'")

    # 3. RFQ Issuance
    rfq_id = "RFQ-2026-999001"
    print(f"\n[STEP 3: COMPETITIVE RFQ DISPATCH]")
    print(f"  RFQ ID            : {rfq_id}")
    print(f"  Dispatched To     : 3 Certified Hardware Suppliers")
    print(f"  Submission Window : 14 Calendar Days")

    # 4. Supplier Quotes & Landed Cost Comparison
    supplier_a = Supplier(
        supplier_id="SUP-001", supplier_code="APEX", name="Apex Technologies",
        category=ItemCategory.HARDWARE, contact_email="sales@apex.com",
        currency=Currency.USD, payment_terms=PaymentTerms.NET_30,
        performance_rating=4.9, risk_level="LOW", is_active=True,
        on_time_delivery_rate=0.98, quality_score=0.99, created_at="2025-01-01"
    )
    supplier_b = Supplier(
        supplier_id="SUP-002", supplier_code="DELL", name="Dell Enterprise Direct",
        category=ItemCategory.HARDWARE, contact_email="gov@dell.com",
        currency=Currency.USD, payment_terms=PaymentTerms.NET_45,
        performance_rating=4.7, risk_level="LOW", is_active=True,
        on_time_delivery_rate=0.94, quality_score=0.96, created_at="2025-01-01"
    )
    supplier_c = Supplier(
        supplier_id="SUP-003", supplier_code="TECH", name="TechPro Components (EU)",
        category=ItemCategory.HARDWARE, contact_email="orders@techpro.eu",
        currency=Currency.EUR, payment_terms=PaymentTerms.NET_30,
        performance_rating=4.1, risk_level="MEDIUM", is_active=True,
        on_time_delivery_rate=0.88, quality_score=0.91, created_at="2025-01-01"
    )

    # Calculate 3 quotes
    from src.models.entities import SupplierQuote
    q1 = SupplierQuote(
        quote_id="QUO-APEX-2026-999001", rfq_id=rfq_id, supplier_id="SUP-001",
        quote_date=req_date.strftime("%Y-%m-%d"), validity_end_date=(req_date + timedelta(days=60)).strftime("%Y-%m-%d"),
        currency=Currency.USD, exchange_rate_to_usd=1.0,
        base_amount=46000.0, freight_cost=350.0, tax_duty_amount=0.0, discount_amount=1000.0,
        total_landed_cost_usd=calculate_landed_cost(46000.0, 1000.0, 350.0, 0.0, 1.0),
        promised_lead_time_days=6, payment_terms=PaymentTerms.NET_30, warranty_months=24,
        quote_status=QuoteStatus.SUBMITTED, landed_cost_rank=1, selection_score=0.0
    )
    q2 = SupplierQuote(
        quote_id="QUO-DELL-2026-999002", rfq_id=rfq_id, supplier_id="SUP-002",
        quote_date=req_date.strftime("%Y-%m-%d"), validity_end_date=(req_date + timedelta(days=45)).strftime("%Y-%m-%d"),
        currency=Currency.USD, exchange_rate_to_usd=1.0,
        base_amount=47200.0, freight_cost=150.0, tax_duty_amount=0.0, discount_amount=500.0,
        total_landed_cost_usd=calculate_landed_cost(47200.0, 500.0, 150.0, 0.0, 1.0),
        promised_lead_time_days=14, payment_terms=PaymentTerms.NET_45, warranty_months=12,
        quote_status=QuoteStatus.SUBMITTED, landed_cost_rank=2, selection_score=0.0
    )
    q3 = SupplierQuote(
        quote_id="QUO-TECH-2026-999003", rfq_id=rfq_id, supplier_id="SUP-003",
        quote_date=req_date.strftime("%Y-%m-%d"), validity_end_date=(req_date + timedelta(days=30)).strftime("%Y-%m-%d"),
        currency=Currency.EUR, exchange_rate_to_usd=1.08,
        base_amount=41000.0, freight_cost=1200.0, tax_duty_amount=1400.0, discount_amount=0.0,
        total_landed_cost_usd=calculate_landed_cost(41000.0, 0.0, 1200.0, 1400.0, 1.08),
        promised_lead_time_days=22, payment_terms=PaymentTerms.NET_30, warranty_months=12,
        quote_status=QuoteStatus.SUBMITTED, landed_cost_rank=3, selection_score=0.0
    )

    supp_map = {"SUP-001": supplier_a, "SUP-002": supplier_b, "SUP-003": supplier_c}
    ranked = rank_and_score_quotes([q1, q2, q3], supp_map)

    print(f"\n[STEP 4: QUOTE COMPARISON MATRIX (TOTAL LANDED COST & SCORING)]")
    print(f"  {'Supplier':<24} | {'Base (Cur)':<12} | {'Freight/Tariff':<15} | {'Landed (USD)':<13} | {'Lead':<6} | {'Score':<6} | {'Status'}")
    print("  " + "-" * 95)
    for q in ranked:
        s = supp_map[q.supplier_id]
        print(f"  {s.name:<24} | {q.currency.value} {q.base_amount:>8,.0f} | ${q.freight_cost + q.tax_duty_amount:>13,.2f} | ${q.total_landed_cost_usd:>11,.2f} | {q.promised_lead_time_days:>2} d  | {q.selection_score:>5.1f} | Rank #{q.landed_cost_rank}")

    # 5. Award Selection
    winner = ranked[0]
    winning_supp = supp_map[winner.supplier_id]
    rationale = generate_award_rationale(winner, ranked[0], winning_supp)
    print(f"\n[STEP 5: SUPPLIER AWARD & AUDIT RATIONALE]")
    print(f"  Awarded Supplier  : {winning_supp.name} ({winner.quote_id})")
    print(f"  Award Rationale   : {rationale}")

    # 6. Purchase Order Generation
    po_id = "PO-2026-999001"
    po_date = req_date + timedelta(days=2)
    print(f"\n[STEP 6: PURCHASE ORDER ISSUED]")
    print(f"  PO ID             : {po_id}")
    print(f"  Contract Value    : ${winner.total_landed_cost_usd:,.2f}")
    print(f"  Line Parity Check : 1 PO Line (${winner.total_landed_cost_usd:,.2f}) == Quote Line Total (100% Match)")
    print(f"  Approval Attached : {approval_id}")
    print(f"  Status            : ISSUED")

    # 7. Delivery Execution & Quality Inspection
    deliv_id = f"DEL-{po_id}-01"
    deliv_date = po_date + timedelta(days=winner.promised_lead_time_days)
    print(f"\n[STEP 7: INBOUND LOGISTICS & DELIVERY VERIFICATION]")
    print(f"  Delivery ID       : {deliv_id}")
    print(f"  Carrier & Tracking: FEDEX (Tracking: FDX-88492019)")
    print(f"  Arrival Date      : {deliv_date.strftime('%Y-%m-%d')} (Promised: {winner.promised_lead_time_days} days)")
    print(f"  Delivery Status   : DELIVERED_ON_TIME")
    print(f"  Receiving Inspect : PASSED (5/5 Units verified functional)")
    print(f"  Final Order State : FULFILLED (Spend Realized)")

    print("\n" + "=" * 70)
    print("  [SUCCESS] End-to-End Workflow successfully completed with full audit trail!")
    print("=" * 70)


if __name__ == "__main__":
    run_simulation()

