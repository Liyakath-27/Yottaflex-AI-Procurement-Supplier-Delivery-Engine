
-- Schema definition for Procurement & Supplier Delivery System

CREATE TABLE IF NOT EXISTS departments (
    department_id TEXT PRIMARY KEY,
    department_name TEXT NOT NULL,
    category TEXT NOT NULL,
    cost_center_code TEXT UNIQUE NOT NULL,
    head_requester_id TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS budgets (
    budget_id TEXT PRIMARY KEY,
    department_id TEXT NOT NULL,
    fiscal_year INTEGER NOT NULL,
    category TEXT NOT NULL,
    allocated_amount REAL NOT NULL,
    committed_amount REAL NOT NULL DEFAULT 0.0,
    spent_amount REAL NOT NULL DEFAULT 0.0,
    remaining_balance REAL NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
);

CREATE TABLE IF NOT EXISTS requesters (
    requester_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    department_id TEXT NOT NULL,
    role TEXT NOT NULL,
    approval_limit REAL NOT NULL DEFAULT 0.0,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY (department_id) REFERENCES departments(department_id)
);

CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id TEXT PRIMARY KEY,
    supplier_code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    contact_email TEXT NOT NULL,
    currency TEXT NOT NULL,
    payment_terms TEXT NOT NULL,
    performance_rating REAL NOT NULL,
    risk_level TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    on_time_delivery_rate REAL NOT NULL,
    quality_score REAL NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS purchase_requests (
    request_id TEXT PRIMARY KEY,
    requester_id TEXT NOT NULL,
    department_id TEXT NOT NULL,
    budget_id TEXT NOT NULL,
    request_date TEXT NOT NULL,
    required_date TEXT NOT NULL,
    status TEXT NOT NULL,
    category TEXT NOT NULL,
    priority TEXT NOT NULL,
    total_estimated_amount REAL NOT NULL,
    currency TEXT NOT NULL,
    procurement_method TEXT NOT NULL,
    single_source_justification TEXT,
    is_split_purchase INTEGER NOT NULL DEFAULT 0,
    approval_tier_required TEXT NOT NULL,
    FOREIGN KEY (requester_id) REFERENCES requesters(requester_id),
    FOREIGN KEY (department_id) REFERENCES departments(department_id),
    FOREIGN KEY (budget_id) REFERENCES budgets(budget_id)
);

CREATE TABLE IF NOT EXISTS request_lines (
    line_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    item_description TEXT NOT NULL,
    item_category TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_of_measure TEXT NOT NULL,
    estimated_unit_price REAL NOT NULL,
    estimated_line_total REAL NOT NULL,
    FOREIGN KEY (request_id) REFERENCES purchase_requests(request_id)
);

CREATE TABLE IF NOT EXISTS rfqs (
    rfq_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    issue_date TEXT NOT NULL,
    submission_deadline TEXT NOT NULL,
    status TEXT NOT NULL,
    target_currency TEXT NOT NULL,
    min_quotes_required INTEGER NOT NULL DEFAULT 3,
    quotes_received_count INTEGER NOT NULL DEFAULT 0,
    award_date TEXT,
    awarded_supplier_id TEXT,
    awarded_quote_id TEXT,
    FOREIGN KEY (request_id) REFERENCES purchase_requests(request_id),
    FOREIGN KEY (awarded_supplier_id) REFERENCES suppliers(supplier_id)
);

CREATE TABLE IF NOT EXISTS supplier_quotes (
    quote_id TEXT PRIMARY KEY,
    rfq_id TEXT NOT NULL,
    supplier_id TEXT NOT NULL,
    quote_date TEXT NOT NULL,
    validity_end_date TEXT NOT NULL,
    currency TEXT NOT NULL,
    exchange_rate_to_usd REAL NOT NULL DEFAULT 1.0,
    base_amount REAL NOT NULL,
    freight_cost REAL NOT NULL DEFAULT 0.0,
    tax_duty_amount REAL NOT NULL DEFAULT 0.0,
    discount_amount REAL NOT NULL DEFAULT 0.0,
    total_landed_cost_usd REAL NOT NULL,
    promised_lead_time_days INTEGER NOT NULL,
    payment_terms TEXT NOT NULL,
    warranty_months INTEGER NOT NULL DEFAULT 12,
    quote_status TEXT NOT NULL,
    landed_cost_rank INTEGER NOT NULL,
    selection_score REAL NOT NULL,
    award_rationale TEXT,
    FOREIGN KEY (rfq_id) REFERENCES rfqs(rfq_id),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
);

CREATE TABLE IF NOT EXISTS quote_lines (
    quote_line_id TEXT PRIMARY KEY,
    quote_id TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    item_description TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    line_total REAL NOT NULL,
    FOREIGN KEY (quote_id) REFERENCES supplier_quotes(quote_id)
);

CREATE TABLE IF NOT EXISTS approvals (
    approval_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    tier_level TEXT NOT NULL,
    approver_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    decision_date TEXT NOT NULL,
    amount_evaluated REAL NOT NULL,
    approver_limit_at_decision REAL NOT NULL,
    comments TEXT,
    is_override INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (approver_id) REFERENCES requesters(requester_id)
);

CREATE TABLE IF NOT EXISTS purchase_orders (
    po_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL,
    rfq_id TEXT,
    quote_id TEXT,
    supplier_id TEXT NOT NULL,
    po_date TEXT NOT NULL,
    required_delivery_date TEXT NOT NULL,
    status TEXT NOT NULL,
    currency TEXT NOT NULL,
    total_po_amount REAL NOT NULL,
    payment_terms TEXT NOT NULL,
    delivery_address TEXT NOT NULL,
    approval_reference_id TEXT,
    FOREIGN KEY (request_id) REFERENCES purchase_requests(request_id),
    FOREIGN KEY (rfq_id) REFERENCES rfqs(rfq_id),
    FOREIGN KEY (quote_id) REFERENCES supplier_quotes(quote_id),
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
);

CREATE TABLE IF NOT EXISTS po_lines (
    po_line_id TEXT PRIMARY KEY,
    po_id TEXT NOT NULL,
    line_number INTEGER NOT NULL,
    item_description TEXT NOT NULL,
    quantity_ordered INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    line_amount REAL NOT NULL,
    quantity_received INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (po_id) REFERENCES purchase_orders(po_id)
);

CREATE TABLE IF NOT EXISTS deliveries (
    delivery_id TEXT PRIMARY KEY,
    po_id TEXT NOT NULL,
    shipment_number INTEGER NOT NULL DEFAULT 1,
    delivery_date TEXT NOT NULL,
    carrier TEXT NOT NULL,
    tracking_number TEXT NOT NULL,
    delivery_status TEXT NOT NULL,
    received_by_user_id TEXT NOT NULL,
    inspection_status TEXT NOT NULL,
    items_delivered_count INTEGER NOT NULL,
    is_partial INTEGER NOT NULL DEFAULT 0,
    notes TEXT,
    FOREIGN KEY (po_id) REFERENCES purchase_orders(po_id),
    FOREIGN KEY (received_by_user_id) REFERENCES requesters(requester_id)
);

CREATE TABLE IF NOT EXISTS audit_events (
    event_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    event_timestamp TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    previous_state TEXT,
    new_state TEXT NOT NULL,
    action_type TEXT NOT NULL,
    details TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ground_truth (
    anomaly_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    issue_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    rule_violated TEXT NOT NULL,
    description TEXT NOT NULL,
    detection_criteria TEXT NOT NULL,
    injected_at_stage TEXT NOT NULL,
    expected_audit_verdict TEXT NOT NULL
);
