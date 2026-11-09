"""
Reusable Workflow Simulation Engine.
Executes an end-to-end procurement transaction programmatically,
returning structured JSON results and audit logs.
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta
import random

from src.models.enums import (
    ItemCategory, Currency, PaymentTerms,
    ApprovalDecision, QuoteStatus, PurchaseOrderStatus,
    DeliveryStatus, InspectionStatus, Carrier
)
from src.engine.approval_matrix import get_required_tier
from src.engine.quote_comparator import calculate_landed_cost, rank_and_score_quotes, generate_award_rationale
from src.models.entities import Supplier, SupplierQuote


def execute_simulated_workflow(
    item_name: str = "Developer Workstation Dual GPU 64GB",
    quantity: int = 5,
    estimated_unit_price: float = 3200.0,
    department_name: str = "Engineering & Software",
    requester_name: str = "Alex Morgan (Senior Engineer)",
    category: str = "HARDWARE",
) -> Dict[str, Any]:
    """Execute complete end-to-end procurement simulation."""
    total_amount = round(quantity * estimated_unit_price, 2)
    pr_id = f"PR-2026-{random.randint(900000, 999999)}"
    now = datetime.now()
    tier = get_required_tier(total_amount)

    # 1. PR Created
    pr_step = {
        "step": 1,
        "name": "Purchase Request Creation",
        "request_id": pr_id,
        "originator": requester_name,
        "department": department_name,
        "item": item_name,
        "quantity": quantity,
        "unit_price_usd": estimated_unit_price,
        "total_amount_usd": total_amount,
        "approval_tier_required": tier.value,
        "procurement_method": "COMPETITIVE_BID",
        "status": "SUBMITTED",
        "timestamp": now.isoformat(),
    }

    # 2. Approval Matrix Check
    approval_id = f"APP-2026-{random.randint(900000, 999999)}"
    approver = "Marcus Vance (Department Director)" if total_amount >= 10000 else "Sarah Jenkins (Team Manager)"
    app_step = {
        "step": 2,
        "name": "Multi-Tier Approval Decision",
        "approval_id": approval_id,
        "approver": approver,
        "decision": "APPROVED",
        "amount_evaluated": total_amount,
        "comments": "Approved within FY2026 departmental CapEx budget envelope.",
        "timestamp": (now + timedelta(hours=2)).isoformat(),
    }

    # 3. RFQ Dispatch
    rfq_id = f"RFQ-2026-{random.randint(900000, 999999)}"
    rfq_step = {
        "step": 3,
        "name": "Competitive RFQ Issuance",
        "rfq_id": rfq_id,
        "request_id": pr_id,
        "min_quotes_required": 3,
        "submission_deadline": (now + timedelta(days=14)).strftime("%Y-%m-%d"),
        "status": "OPEN",
    }

    # 4. Solicit 3 Quotes
    s1 = Supplier(
        supplier_id="SUP-001", supplier_code="APEX01", name="Apex Technologies",
        category=ItemCategory.HARDWARE, contact_email="sales@apex.com",
        currency=Currency.USD, payment_terms=PaymentTerms.NET_30,
        performance_rating=4.9, risk_level="LOW", is_active=True,
        on_time_delivery_rate=0.98, quality_score=0.99, created_at="2025-01-01"
    )
    s2 = Supplier(
        supplier_id="SUP-002", supplier_code="DELL02", name="Dell Enterprise Direct",
        category=ItemCategory.HARDWARE, contact_email="gov@dell.com",
        currency=Currency.USD, payment_terms=PaymentTerms.NET_45,
        performance_rating=4.7, risk_level="LOW", is_active=True,
        on_time_delivery_rate=0.94, quality_score=0.96, created_at="2025-01-01"
    )
    s3 = Supplier(
        supplier_id="SUP-003", supplier_code="TECH03", name="TechPro Components (EU)",
        category=ItemCategory.HARDWARE, contact_email="orders@techpro.eu",
        currency=Currency.EUR, payment_terms=PaymentTerms.NET_30,
        performance_rating=4.2, risk_level="MEDIUM", is_active=True,
        on_time_delivery_rate=0.88, quality_score=0.91, created_at="2025-01-01"
    )
    supp_map = {"SUP-001": s1, "SUP-002": s2, "SUP-003": s3}

    base_1 = round(total_amount * 0.96, 2)
    q1 = SupplierQuote(
        quote_id=f"QUO-APEX01-2026-{random.randint(100000, 999999)}",
        rfq_id=rfq_id, supplier_id="SUP-001",
        quote_date=now.strftime("%Y-%m-%d"),
        validity_end_date=(now + timedelta(days=60)).strftime("%Y-%m-%d"),
        currency=Currency.USD, exchange_rate_to_usd=1.0,
        base_amount=base_1, freight_cost=250.0, tax_duty_amount=0.0, discount_amount=500.0,
        total_landed_cost_usd=calculate_landed_cost(base_1, 500.0, 250.0, 0.0, 1.0),
        promised_lead_time_days=6, payment_terms=PaymentTerms.NET_30, warranty_months=24,
        quote_status=QuoteStatus.SUBMITTED, landed_cost_rank=1, selection_score=0.0
    )

    base_2 = round(total_amount * 0.99, 2)
    q2 = SupplierQuote(
        quote_id=f"QUO-DELL02-2026-{random.randint(100000, 999999)}",
        rfq_id=rfq_id, supplier_id="SUP-002",
        quote_date=now.strftime("%Y-%m-%d"),
        validity_end_date=(now + timedelta(days=45)).strftime("%Y-%m-%d"),
        currency=Currency.USD, exchange_rate_to_usd=1.0,
        base_amount=base_2, freight_cost=150.0, tax_duty_amount=0.0, discount_amount=300.0,
        total_landed_cost_usd=calculate_landed_cost(base_2, 300.0, 150.0, 0.0, 1.0),
        promised_lead_time_days=12, payment_terms=PaymentTerms.NET_45, warranty_months=12,
        quote_status=QuoteStatus.SUBMITTED, landed_cost_rank=2, selection_score=0.0
    )

    base_3 = round(total_amount * 0.88 / 1.08, 2)
    q3 = SupplierQuote(
        quote_id=f"QUO-TECH03-2026-{random.randint(100000, 999999)}",
        rfq_id=rfq_id, supplier_id="SUP-003",
        quote_date=now.strftime("%Y-%m-%d"),
        validity_end_date=(now + timedelta(days=30)).strftime("%Y-%m-%d"),
        currency=Currency.EUR, exchange_rate_to_usd=1.08,
        base_amount=base_3, freight_cost=800.0, tax_duty_amount=1000.0, discount_amount=0.0,
        total_landed_cost_usd=calculate_landed_cost(base_3, 0.0, 800.0, 1000.0, 1.08),
        promised_lead_time_days=21, payment_terms=PaymentTerms.NET_30, warranty_months=12,
        quote_status=QuoteStatus.SUBMITTED, landed_cost_rank=3, selection_score=0.0
    )

    ranked_quotes = rank_and_score_quotes([q1, q2, q3], supp_map)
    winner = ranked_quotes[0]
    winning_supp = supp_map[winner.supplier_id]
    rationale = generate_award_rationale(winner, ranked_quotes[0], winning_supp)

    award_step = {
        "step": 4,
        "name": "Landed Cost Comparison & Supplier Award",
        "quotes_compared": [
            {
                "quote_id": q.quote_id,
                "supplier_name": supp_map[q.supplier_id].name,
                "currency": q.currency.value,
                "base_amount": q.base_amount,
                "freight": q.freight_cost,
                "duty": q.tax_duty_amount,
                "total_landed_cost_usd": q.total_landed_cost_usd,
                "lead_time_days": q.promised_lead_time_days,
                "selection_score": q.selection_score,
                "rank": q.landed_cost_rank,
            }
            for q in ranked_quotes
        ],
        "awarded_quote_id": winner.quote_id,
        "awarded_supplier": winning_supp.name,
        "awarded_landed_cost_usd": winner.total_landed_cost_usd,
        "award_rationale": rationale,
    }

    # 5. PO Generation
    po_id = f"PO-2026-{random.randint(900000, 999999)}"
    po_step = {
        "step": 5,
        "name": "Purchase Order Issuance",
        "po_id": po_id,
        "request_id": pr_id,
        "supplier": winning_supp.name,
        "total_po_amount_usd": winner.total_landed_cost_usd,
        "po_date": (now + timedelta(days=1)).strftime("%Y-%m-%d"),
        "required_delivery_date": (now + timedelta(days=1 + winner.promised_lead_time_days)).strftime("%Y-%m-%d"),
        "approval_reference_id": approval_id,
        "status": "ISSUED",
    }

    # 6. Delivery Verification
    deliv_id = f"DEL-{po_id}-01"
    deliv_step = {
        "step": 6,
        "name": "Inbound Shipment & Receiving Inspection",
        "delivery_id": deliv_id,
        "po_id": po_id,
        "carrier": "FEDEX",
        "tracking_number": f"FDX-{random.randint(10000000, 99999999)}",
        "delivery_status": "DELIVERED_ON_TIME",
        "inspection_status": "PASSED",
        "items_delivered_count": quantity,
        "notes": f"All {quantity} units received in full and verified functional.",
        "final_po_status": "FULFILLED",
    }

    return {
        "success": True,
        "message": f"Successfully executed workflow for '{item_name}' (Total: ${winner.total_landed_cost_usd:,.2f})",
        "summary": {
            "request_id": pr_id,
            "approval_id": approval_id,
            "rfq_id": rfq_id,
            "awarded_quote_id": winner.quote_id,
            "purchase_order_id": po_id,
            "delivery_id": deliv_id,
            "contract_value_usd": winner.total_landed_cost_usd,
            "lifecycle_state": "FULFILLED",
        },
        "steps": [pr_step, app_step, rfq_step, award_step, po_step, deliv_step],
    }

