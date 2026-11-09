"""
Domain Entities and Data Classes for the Procurement & Supplier Delivery System.
"""
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, Field
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


class Department(BaseModel):
    department_id: str = Field(..., description="Unique Department Identifier (DEPT-XXX)")
    department_name: str = Field(..., description="Department operational name")
    category: DepartmentCategory = Field(..., description="Category group")
    cost_center_code: str = Field(..., description="Cost center code (CC-XXXX)")
    head_requester_id: Optional[str] = Field(None, description="FK to Requester managing the dept")
    is_active: bool = Field(True, description="Whether department is active")


class Budget(BaseModel):
    budget_id: str = Field(..., description="Unique Budget Identifier (BUD-2026-XXX)")
    department_id: str = Field(..., description="FK to Department")
    fiscal_year: int = Field(2026, description="Fiscal year")
    category: ItemCategory = Field(..., description="Expense category")
    allocated_amount: float = Field(..., ge=0.0, description="Total allocated budget in USD")
    committed_amount: float = Field(0.0, ge=0.0, description="Encumbered/committed budget in USD")
    spent_amount: float = Field(0.0, ge=0.0, description="Actual realized spend in USD")
    remaining_balance: float = Field(..., description="Calculated remaining balance in USD")
    start_date: str = Field(..., description="Budget start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="Budget end date (YYYY-MM-DD)")
    status: BudgetStatus = Field(BudgetStatus.ACTIVE, description="Budget health status")


class Requester(BaseModel):
    requester_id: str = Field(..., description="Unique Requester Identifier (REQ-XXXX)")
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Corporate email address")
    department_id: str = Field(..., description="FK to Department")
    role: RequesterRole = Field(..., description="Organizational role")
    approval_limit: float = Field(0.0, ge=0.0, description="Authorized signing authority in USD")
    is_active: bool = Field(True, description="Active employee status")
    created_at: str = Field(..., description="Account creation timestamp")


class Supplier(BaseModel):
    supplier_id: str = Field(..., description="Unique Supplier Identifier (SUP-XXX)")
    supplier_code: str = Field(..., description="Short supplier code (e.g. ACME, DELL)")
    name: str = Field(..., description="Supplier company name")
    category: ItemCategory = Field(..., description="Primary category supplied")
    contact_email: str = Field(..., description="Primary contact email")
    currency: Currency = Field(Currency.USD, description="Native currency")
    payment_terms: PaymentTerms = Field(PaymentTerms.NET_30, description="Standard payment terms")
    performance_rating: float = Field(..., ge=1.0, le=5.0, description="Rating out of 5.0")
    risk_level: SupplierRiskLevel = Field(SupplierRiskLevel.LOW, description="Assessed supplier risk")
    is_active: bool = Field(True, description="Whether supplier is qualified/active")
    on_time_delivery_rate: float = Field(..., ge=0.0, le=1.0, description="Historical on-time delivery rate")
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Historical quality inspection pass rate")
    created_at: str = Field(..., description="Supplier onboarding timestamp")


class RequestLine(BaseModel):
    line_id: str = Field(..., description="Unique Line Identifier (PR-2026-XXXXXX-LXX)")
    request_id: str = Field(..., description="FK to PurchaseRequest")
    line_number: int = Field(..., ge=1, description="Sequential line index")
    item_description: str = Field(..., description="Description of requested goods/services")
    item_category: ItemCategory = Field(..., description="Category of the line item")
    quantity: int = Field(..., gt=0, description="Requested quantity")
    unit_of_measure: str = Field("EA", description="Unit of measure (EA, BOX, LICENSE, etc.)")
    estimated_unit_price: float = Field(..., gt=0.0, description="Estimated price per unit in USD")
    estimated_line_total: float = Field(..., gt=0.0, description="quantity * estimated_unit_price")


class PurchaseRequest(BaseModel):
    request_id: str = Field(..., description="Unique PR Identifier (PR-2026-XXXXXX)")
    requester_id: str = Field(..., description="FK to Requester")
    department_id: str = Field(..., description="FK to Department")
    budget_id: str = Field(..., description="FK to Budget")
    request_date: str = Field(..., description="Submission timestamp")
    required_date: str = Field(..., description="Required by delivery date")
    status: PurchaseRequestStatus = Field(..., description="Lifecycle status")
    category: ItemCategory = Field(..., description="Dominant item category")
    priority: PriorityLevel = Field(PriorityLevel.MEDIUM, description="Business priority")
    total_estimated_amount: float = Field(..., ge=0.0, description="Sum of request lines in USD")
    currency: Currency = Field(Currency.USD, description="Request currency")
    procurement_method: ProcurementMethod = Field(..., description="Competitive bid or single-source")
    single_source_justification: Optional[str] = Field(None, description="Documented justification if single source")
    is_split_purchase: bool = Field(False, description="Flag indicating potential split purchase")
    approval_tier_required: ApprovalTier = Field(..., description="Calculated required approval tier")


class RFQ(BaseModel):
    rfq_id: str = Field(..., description="Unique RFQ Identifier (RFQ-2026-XXXXXX)")
    request_id: str = Field(..., description="FK to PurchaseRequest")
    issue_date: str = Field(..., description="RFQ publication timestamp")
    submission_deadline: str = Field(..., description="Quote submission deadline")
    status: RFQStatus = Field(..., description="Current RFQ status")
    target_currency: Currency = Field(Currency.USD, description="Requested quote currency")
    min_quotes_required: int = Field(3, description="Minimum quotes required for award")
    quotes_received_count: int = Field(0, description="Total valid quotes received")
    award_date: Optional[str] = Field(None, description="Date awarded to winning supplier")
    awarded_supplier_id: Optional[str] = Field(None, description="FK to awarded Supplier")
    awarded_quote_id: Optional[str] = Field(None, description="FK to winning SupplierQuote")


class QuoteLine(BaseModel):
    quote_line_id: str = Field(..., description="Unique Quote Line Identifier")
    quote_id: str = Field(..., description="FK to SupplierQuote")
    line_number: int = Field(..., ge=1, description="Corresponding line index")
    item_description: str = Field(..., description="Quoted item description")
    quantity: int = Field(..., gt=0, description="Quoted quantity")
    unit_price: float = Field(..., gt=0.0, description="Quoted unit price in quote currency")
    line_total: float = Field(..., gt=0.0, description="quantity * unit_price")


class SupplierQuote(BaseModel):
    quote_id: str = Field(..., description="Unique Quote Identifier (QUO-<SUP>-2026-XXXXXX)")
    rfq_id: str = Field(..., description="FK to RFQ")
    supplier_id: str = Field(..., description="FK to Supplier")
    quote_date: str = Field(..., description="Date quote submitted")
    validity_end_date: str = Field(..., description="Expiration date of quote pricing")
    currency: Currency = Field(Currency.USD, description="Stated currency")
    exchange_rate_to_usd: float = Field(1.0, gt=0.0, description="FX rate to USD")
    base_amount: float = Field(..., ge=0.0, description="Subtotal of quote lines")
    freight_cost: float = Field(0.0, ge=0.0, description="Shipping/freight charges")
    tax_duty_amount: float = Field(0.0, ge=0.0, description="Taxes and import duties")
    discount_amount: float = Field(0.0, ge=0.0, description="Discounts applied")
    total_landed_cost_usd: float = Field(..., ge=0.0, description="Total landed cost normalized to USD")
    promised_lead_time_days: int = Field(..., ge=1, description="Quoted lead time in calendar days")
    payment_terms: PaymentTerms = Field(PaymentTerms.NET_30, description="Offered payment terms")
    warranty_months: int = Field(12, ge=0, description="Offered warranty in months")
    quote_status: QuoteStatus = Field(..., description="Status of the quote")
    landed_cost_rank: int = Field(..., ge=1, description="Rank among RFQ quotes (1 = lowest cost)")
    selection_score: float = Field(..., description="Multi-factor evaluation score (0-100)")
    award_rationale: Optional[str] = Field(None, description="Auditable justification for award decision")


class Approval(BaseModel):
    approval_id: str = Field(..., description="Unique Approval Identifier (APP-2026-XXXXXX)")
    entity_type: str = Field("PURCHASE_REQUEST", description="Target entity type")
    entity_id: str = Field(..., description="FK to PR or PO")
    tier_level: ApprovalTier = Field(..., description="Approval threshold level")
    approver_id: str = Field(..., description="FK to Requester who approved")
    decision: ApprovalDecision = Field(..., description="Approval decision")
    decision_date: str = Field(..., description="Timestamp of decision")
    amount_evaluated: float = Field(..., ge=0.0, description="Amount evaluated in USD")
    approver_limit_at_decision: float = Field(..., ge=0.0, description="Approver limit at decision time")
    comments: Optional[str] = Field(None, description="Approver comments or rationale")
    is_override: bool = Field(False, description="Whether this was an emergency/override approval")


class POLine(BaseModel):
    po_line_id: str = Field(..., description="Unique PO Line Identifier (PO-2026-XXXXXX-LXX)")
    po_id: str = Field(..., description="FK to PurchaseOrder")
    line_number: int = Field(..., ge=1, description="PO line number")
    item_description: str = Field(..., description="Item ordered")
    quantity_ordered: int = Field(..., gt=0, description="Ordered quantity")
    unit_price: float = Field(..., gt=0.0, description="Unit price in USD")
    line_amount: float = Field(..., gt=0.0, description="quantity_ordered * unit_price")
    quantity_received: int = Field(0, ge=0, description="Total quantity received so far")


class PurchaseOrder(BaseModel):
    po_id: str = Field(..., description="Unique PO Identifier (PO-2026-XXXXXX)")
    request_id: str = Field(..., description="FK to PurchaseRequest")
    rfq_id: Optional[str] = Field(None, description="FK to RFQ if competitive")
    quote_id: Optional[str] = Field(None, description="FK to SupplierQuote if awarded from RFQ")
    supplier_id: str = Field(..., description="FK to Supplier")
    po_date: str = Field(..., description="PO creation timestamp")
    required_delivery_date: str = Field(..., description="Promised/contracted delivery date")
    status: PurchaseOrderStatus = Field(..., description="Lifecycle status")
    currency: Currency = Field(Currency.USD, description="PO currency")
    total_po_amount: float = Field(..., ge=0.0, description="Total PO value in USD (sum of lines)")
    payment_terms: PaymentTerms = Field(PaymentTerms.NET_30, description="Contractual payment terms")
    delivery_address: str = Field(..., description="Designated shipping destination")
    approval_reference_id: Optional[str] = Field(None, description="FK to Approval record")


class Delivery(BaseModel):
    delivery_id: str = Field(..., description="Unique Delivery Identifier (DEL-PO-2026-XXXXXX-XX)")
    po_id: str = Field(..., description="FK to PurchaseOrder")
    shipment_number: int = Field(1, ge=1, description="Sequential shipment number for this PO")
    delivery_date: str = Field(..., description="Recorded arrival date")
    carrier: Carrier = Field(..., description="Shipping carrier")
    tracking_number: str = Field(..., description="Carrier tracking code")
    delivery_status: DeliveryStatus = Field(..., description="Operational delivery outcome")
    received_by_user_id: str = Field(..., description="FK to Requester who accepted delivery")
    inspection_status: InspectionStatus = Field(..., description="Receiving quality inspection status")
    items_delivered_count: int = Field(..., ge=0, description="Total items received in this shipment")
    is_partial: bool = Field(False, description="Whether this is a partial delivery")
    notes: Optional[str] = Field(None, description="Delivery receiving notes")


class AuditEvent(BaseModel):
    event_id: str = Field(..., description="Unique Audit Event Identifier (EVT-XXXXXXXX)")
    entity_type: str = Field(..., description="Entity type affected")
    entity_id: str = Field(..., description="Entity identifier")
    event_timestamp: str = Field(..., description="Timestamp of event occurrence")
    actor_id: str = Field(..., description="FK to Requester or 'SYSTEM'")
    previous_state: Optional[str] = Field(None, description="Previous status/state")
    new_state: str = Field(..., description="New status/state")
    action_type: str = Field(..., description="Action classification")
    details: str = Field(..., description="Detailed audit narrative")


class GroundTruthAnomaly(BaseModel):
    anomaly_id: str = Field(..., description="Unique Anomaly Identifier (ANO-XXXXX)")
    entity_type: str = Field(..., description="Target entity type")
    entity_id: str = Field(..., description="Target entity primary key")
    issue_type: AnomalyType = Field(..., description="Classified anomaly type")
    severity: AnomalySeverity = Field(..., description="Business severity level")
    rule_violated: str = Field(..., description="Governance/business rule identifier")
    description: str = Field(..., description="Explanation of why this is anomalous")
    detection_criteria: str = Field(..., description="Algorithmic criteria to flag this anomaly")
    injected_at_stage: str = Field(..., description="Lifecycle stage where anomaly was introduced")
    expected_audit_verdict: str = Field("NON_COMPLIANT", description="Expected auditor/engine verdict")

