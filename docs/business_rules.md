# Business Rules & Governance Specification

This document details the business logic, governance thresholds, exception paths, and automated compliance auditing rules implemented in the system.

---

## 1. Governance Rules Catalog

### Rule BR-001: Mandatory Approval Before PO Issuance
- **Statement**: No Purchase Order may be issued to a vendor unless it is linked to an authorized, active `Approval` record where `decision == 'APPROVED'`.
- **Severity**: `CRITICAL`
- **Detection Logic**:
  ```sql
  SELECT po_id FROM purchase_orders 
  WHERE approval_reference_id IS NULL 
     OR approval_reference_id NOT IN (SELECT approval_id FROM approvals WHERE decision = 'APPROVED');
  ```
- **Injected Anomaly**: `PO_WITHOUT_APPROVAL`.

---

### Rule BR-002: Quote Pricing Must Be Valid At Award Date
- **Statement**: A supplier quote cannot be awarded if the RFQ award date occurs after the quote's `validity_end_date`.
- **Severity**: `HIGH`
- **Detection Logic**:
  ```sql
  SELECT r.rfq_id, q.quote_id 
  FROM rfqs r
  JOIN supplier_quotes q ON r.awarded_quote_id = q.quote_id
  WHERE q.validity_end_date < r.award_date;
  ```
- **Injected Anomaly**: `QUOTE_EXPIRED_BEFORE_AWARD`.

---

### Rule BR-003: Documented Rationale Required for Non-Cheapest Award
- **Statement**: If an awarded quote does not have the lowest total landed cost among all eligible quotes submitted for that RFQ, the system must retain an auditable explanation in `award_rationale`.
- **Severity**: `HIGH`
- **Detection Logic**:
  ```sql
  SELECT q.quote_id 
  FROM supplier_quotes q
  JOIN rfqs r ON q.rfq_id = r.rfq_id
  WHERE q.quote_id = r.awarded_quote_id 
    AND q.landed_cost_rank > 1 
    AND (q.award_rationale IS NULL OR length(trim(q.award_rationale)) < 15);
  ```
- **Injected Anomaly**: `NON_CHEAPEST_WITHOUT_RATIONALE`.

---

### Rule BR-004: Prohibited Transaction with Inactive Supplier
- **Statement**: Quotes cannot be accepted and Purchase Orders cannot be issued to deactivated or blacklisted suppliers (`is_active = FALSE`).
- **Severity**: `CRITICAL`
- **Detection Logic**:
  ```sql
  SELECT po.po_id 
  FROM purchase_orders po
  JOIN suppliers s ON po.supplier_id = s.supplier_id
  WHERE s.is_active = 0;
  ```
- **Injected Anomaly**: `INACTIVE_SUPPLIER`.

---

### Rule BR-005: Budget Allocation Limit Exceeded
- **Statement**: Total encumbered commitments plus realized spend within any departmental category budget must not exceed `allocated_amount`.
- **Severity**: `HIGH`
- **Detection Logic**:
  ```sql
  SELECT budget_id 
  FROM budgets 
  WHERE (committed_amount + spent_amount) > (allocated_amount + 0.01);
  ```
- **Injected Anomaly**: `BUDGET_OVERRUN`.

---

### Rule BR-006: Duplicate Purchase Request Detection
- **Statement**: Submitting requests with identical line item descriptions, quantities, and prices within a 72-hour rolling window by the same department is prohibited without formal duplicate justification.
- **Severity**: `MEDIUM`
- **Detection Logic**: Identifies matching item signatures submitted within 72 hours.
- **Injected Anomaly**: `DUPLICATE_REQUEST`.

---

### Rule BR-007: Foreign Currency Conversion Omission
- **Statement**: International supplier quotes denominated in foreign currencies (EUR, GBP, CAD) must calculate `total_landed_cost_usd` using the active exchange rate rather than recording 1:1 nominal values.
- **Severity**: `HIGH`
- **Detection Logic**:
  ```python
  abs(quote.exchange_rate_to_usd - 1.0) > 0.05 and abs(quote.total_landed_cost_usd - raw_unconverted) < 1.0
  ```
- **Injected Anomaly**: `QUOTE_CURRENCY_MISMATCH`.

---

### Rule BR-008: Threshold Avoidance via Split Purchase
- **Statement**: Artificially splitting a requirement into multiple smaller orders just below approval threshold boundaries (e.g. $950 - $990) to bypass Tier 2 approval is strictly prohibited.
- **Severity**: `HIGH`
- **Detection Logic**: Evaluates PRs where `is_split_purchase = TRUE`.
- **Injected Anomaly**: `SPLIT_PURCHASE`.

---

## 2. Exception Handling Workflows

### A. Single-Source Exception Path
1. If an item cannot be sourced competitively due to proprietary vendor technology or regulatory requirements, the requester selects `procurement_method = SINGLE_SOURCE`.
2. A mandatory `single_source_justification` must be provided.
3. The request requires approval by the Department Head and Finance Director regardless of the standard threshold.
4. If approved, the workflow bypasses the RFQ phase and generates a PO directly to the certified vendor.

### B. Budget Overrun Exception Path
1. If a PR exceeds the remaining departmental categorical budget balance, it is routed into an overrun review queue.
2. The Finance Director or VP must approve a budget reallocation or authorize an emergency budget override.
3. Unapproved overruns trigger `BUDGET_OVERRUN` and halt PO generation.

### C. Inbound Delivery Exception Paths
1. **On-Time Delivery**: Logistics arrival $\le$ required delivery date. Receiving inspection is passed, PO status becomes `FULFILLED`, and committed budget converts to spent.
2. **Late Delivery**: Logistics arrival $>$ required delivery date. Logged as `DELIVERED_LATE` with transit delay details; supplier on-time rating is adjusted downward.
3. **Partial Delivery**: Goods shipped in two batches (Shipment 1: 60%, Shipment 2: 40%). PO status is set to `PARTIALLY_DELIVERED` until the final shipment passes receiving inspection.
4. **Damaged / Quality Concession**: Packaging dented or inspection concession granted. Logged as `DAMAGED` with `ACCEPTED_WITH_CONCESSION`.

