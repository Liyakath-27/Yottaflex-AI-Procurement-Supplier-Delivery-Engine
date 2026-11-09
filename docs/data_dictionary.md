# Enterprise Procurement & Supplier Delivery — Data Dictionary

This document defines the schema, data types, constraints, allowed enum values, units, and validation rules for all 15 core entities and event tables in the system.

---

## 1. Department (`departments`)
Master entity representing corporate organizational units and cost centers.

| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule & Business Logic |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `department_id` | STRING | Required | `DEPT-\d{3}` (e.g. `DEPT-001`) | ID | Primary Key | Immutable primary key for department. |
| `department_name` | STRING | Required | Printable text (e.g. "Engineering & Software") | N/A | Non-unique | Official operational name of department. |
| `category` | ENUM | Required | `ENGINEERING`, `MARKETING`, `OPERATIONS`, `IT_INFRASTRUCTURE`, `HUMAN_RESOURCES`, `FACILITIES`, `FINANCE`, `LEGAL`, `RESEARCH_DEV`, `CUSTOMER_SUPPORT` | N/A | Non-unique | Department classification group. |
| `cost_center_code` | STRING | Required | `CC-\d{4}` (e.g. `CC-1010`) | Code | Unique | Finance cost allocation code. |
| `head_requester_id` | STRING | Optional | `REQ-\d{4}` | ID | Non-unique | Foreign key referencing `requesters.requester_id` for department manager. |
| `is_active` | BOOLEAN | Required | `TRUE`, `FALSE` (or `1`, `0` in SQL) | Flag | Non-unique | Inactive departments cannot originate new purchase requests. |

---

## 2. Budget (`budgets`)
Master entity defining fiscal year categorical budget ceilings.

| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule & Business Logic |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `budget_id` | STRING | Required | `BUD-2026-\d{3}` (e.g. `BUD-2026-001`) | ID | Primary Key | Immutable primary key for budget envelope. |
| `department_id` | STRING | Required | FK -> `departments.department_id` | ID | Foreign Key | Must reference an existing, active department. |
| `fiscal_year` | INTEGER | Required | `2026` | Year | Non-unique | Fiscal year for budget allocation. |
| `category` | ENUM | Required | `HARDWARE`, `SOFTWARE`, `SERVICES`, `FACILITIES`, `OFFICE_SUPPLIES`, `CONSULTING`, `LOGISTICS` | N/A | Non-unique | Expense category restriction. |
| `allocated_amount` | FLOAT | Required | Real numbers $\ge 0.0$ | USD | Non-unique | Total approved budget ceiling. |
| `committed_amount` | FLOAT | Required | Real numbers $\ge 0.0$ | USD | Non-unique | Encumbered by approved PRs / open POs. |
| `spent_amount` | FLOAT | Required | Real numbers $\ge 0.0$ | USD | Non-unique | Realized upon delivery fulfillment. |
| `remaining_balance` | FLOAT | Required | Calculated: `allocated_amount - committed - spent` | USD | Non-unique | Must satisfy arithmetic reconciliation. Negative balance indicates overrun. |
| `start_date` | STRING | Required | ISO-8601 Date (`YYYY-MM-DD`) | Date | Non-unique | Standard fiscal start (`2026-01-01`). |
| `end_date` | STRING | Required | ISO-8601 Date (`YYYY-MM-DD`) | Date | Non-unique | Standard fiscal end (`2026-12-31`). |
| `status` | ENUM | Required | `ACTIVE`, `FROZEN`, `DEPLETED`, `CLOSED` | N/A | Non-unique | If `remaining_balance <= 0.0`, status is `DEPLETED`. |

---

## 3. Requester (`requesters`)
Master entity representing corporate employees who request or approve purchases.

| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule & Business Logic |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `requester_id` | STRING | Required | `REQ-\d{4}` (e.g. `REQ-0001`) | ID | Primary Key | Immutable employee requester ID. |
| `name` | STRING | Required | First and Last name | N/A | Non-unique | Legal employee name. |
| `email` | STRING | Required | `<name>@yottaflex.ai` | Email | Unique | Unique corporate email address. |
| `department_id` | STRING | Required | FK -> `departments.department_id` | ID | Foreign Key | Must reference valid department. |
| `role` | ENUM | Required | `JUNIOR_ANALYST`, `STAFF_SPECIALIST`, `SENIOR_ENGINEER`, `TEAM_LEAD`, `DEPARTMENT_MANAGER`, `DIRECTOR`, `VP` | N/A | Non-unique | Organizational authority tier. |
| `approval_limit` | FLOAT | Required | Real numbers $\ge 0.0$ | USD | Non-unique | Max signing limit ($0, $1K, $5K, $10K, $50K, $150K, $500K). |
| `is_active` | BOOLEAN | Required | `TRUE`, `FALSE` | Flag | Non-unique | Inactive requesters cannot approve or submit PRs. |
| `created_at` | STRING | Required | ISO-8601 Timestamp | DateTime | Non-unique | Timestamp of employee profile creation. |

---

## 4. Supplier (`suppliers`)
Master entity tracking external commercial vendors and performance ratings.

| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule & Business Logic |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `supplier_id` | STRING | Required | `SUP-\d{3}` (e.g. `SUP-001`) | ID | Primary Key | Immutable vendor identifier. |
| `supplier_code` | STRING | Required | 4-6 alphanumeric characters (e.g. `APEX01`) | Code | Unique | Short code used in quote IDs. |
| `name` | STRING | Required | Commercial company name | N/A | Non-unique | Registered company legal name. |
| `category` | ENUM | Required | Same as `ItemCategory` | N/A | Non-unique | Supplier primary supply category. |
| `contact_email` | STRING | Required | `procurement@<supplier>.com` | Email | Non-unique | Contact email for RFQ dispatch. |
| `currency` | ENUM | Required | `USD`, `EUR`, `GBP`, `CAD` | ISO-4217 | Non-unique | Supplier native billing currency. |
| `payment_terms` | ENUM | Required | `NET_15`, `NET_30`, `NET_45`, `NET_60`, `DUE_ON_RECEIPT` | Terms | Non-unique | Standard commercial terms. |
| `performance_rating` | FLOAT | Required | $1.00 \le \text{rating} \le 5.00$ | Score | Non-unique | Historical composite rating out of 5. |
| `risk_level` | ENUM | Required | `LOW`, `MEDIUM`, `HIGH`, `CRITICAL` | N/A | Non-unique | Evaluated compliance risk level. |
| `is_active` | BOOLEAN | Required | `TRUE`, `FALSE` | Flag | Non-unique | Inactive vendors cannot be awarded quotes or POs. |
| `on_time_delivery_rate` | FLOAT | Required | $0.00 \le \text{rate} \le 1.00$ | Ratio | Non-unique | Historical on-time shipment rate. |
| `quality_score` | FLOAT | Required | $0.00 \le \text{score} \le 1.00$ | Ratio | Non-unique | Receiving inspection pass rate. |
| `created_at` | STRING | Required | ISO-8601 Timestamp | DateTime | Non-unique | Vendor onboarding timestamp. |

---

## 5. Purchase Request (`purchase_requests`)
Transactional document capturing purchase intent and approval routing.

| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule & Business Logic |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `request_id` | STRING | Required | `PR-2026-\d{6}` (e.g. `PR-2026-000001`) | ID | Primary Key | Immutable PR identifier. |
| `requester_id` | STRING | Required | FK -> `requesters.requester_id` | ID | Foreign Key | Originator of request. |
| `department_id` | STRING | Required | FK -> `departments.department_id` | ID | Foreign Key | Charging department. |
| `budget_id` | STRING | Required | FK -> `budgets.budget_id` | ID | Foreign Key | Target budget envelope. |
| `request_date` | STRING | Required | ISO-8601 Timestamp | DateTime | Non-unique | Submission timestamp. |
| `required_date` | STRING | Required | ISO-8601 Timestamp ($\ge \text{request\_date}$) | DateTime | Non-unique | Promised delivery requirement. |
| `status` | ENUM | Required | `DRAFT`, `SUBMITTED`, `PENDING_APPROVAL`, `APPROVED`, `REJECTED`, `IN_SOURCING`, `PO_CREATED`, `CANCELLED` | N/A | Non-unique | Lifecycle state machine status. |
| `category` | ENUM | Required | Same as `ItemCategory` | N/A | Non-unique | Predominant category of goods. |
| `priority` | ENUM | Required | `LOW`, `MEDIUM`, `HIGH`, `URGENT` | N/A | Non-unique | Business urgency indicator. |
| `total_estimated_amount` | FLOAT | Required | Real number $\ge 0.0$ | USD | Non-unique | Must equal exact sum of `request_lines`. |
| `currency` | ENUM | Required | `USD` | ISO-4217 | Non-unique | Corporate reporting currency. |
| `procurement_method` | ENUM | Required | `COMPETITIVE_BID`, `SINGLE_SOURCE`, `CATALOG_DIRECT` | N/A | Non-unique | Sourcing strategy. |
| `single_source_justification` | STRING | Optional | Text explanation | N/A | Non-unique | Mandatory if `procurement_method == SINGLE_SOURCE`. |
| `is_split_purchase` | BOOLEAN | Required | `TRUE`, `FALSE` | Flag | Non-unique | Flags suspicious sub-threshold splitting. |
| `approval_tier_required` | ENUM | Required | `TIER_1_MANAGER`, `TIER_2_DEPT_HEAD`, `TIER_3_FINANCE_DIR`, `TIER_4_EXECUTIVE` | N/A | Non-unique | Calculated deterministically from `total_estimated_amount`. |

---

## 6. Request Line (`request_lines`)
Child line item breakdown of a purchase request.

| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule & Business Logic |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `line_id` | STRING | Required | `PR-2026-\d{6}-L\d{2}` | ID | Primary Key | Composite key with PR ID and line number. |
| `request_id` | STRING | Required | FK -> `purchase_requests.request_id` | ID | Foreign Key | Valid parent PR ID. |
| `line_number` | INTEGER | Required | Sequential integer $\ge 1$ | Index | Non-unique | Index within PR. |
| `item_description` | STRING | Required | Item description text | N/A | Non-unique | Clear description of item or service. |
| `item_category` | ENUM | Required | Same as `ItemCategory` | N/A | Non-unique | Classification category. |
| `quantity` | INTEGER | Required | Integer $> 0$ | Count | Non-unique | Units requested. |
| `unit_of_measure` | STRING | Required | `EA`, `BOX`, `LICENSE`, `MONTH`, `HOUR`, `PROJECT` | UOM | Non-unique | Unit of measurement. |
| `estimated_unit_price` | FLOAT | Required | Real number $> 0.0$ | USD | Non-unique | Target unit cost. |
| `estimated_line_total` | FLOAT | Required | Calculated: `quantity * estimated_unit_price` | USD | Non-unique | Exact arithmetic product. |

---

## 7. RFQ (`rfqs`)
Request for Quotation issued to external suppliers.

| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule & Business Logic |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `rfq_id` | STRING | Required | `RFQ-2026-\d{6}` | ID | Primary Key | Immutable RFQ ID. |
| `request_id` | STRING | Required | FK -> `purchase_requests.request_id` | ID | Foreign Key | Sourcing source PR. |
| `issue_date` | STRING | Required | ISO-8601 Timestamp ($\ge \text{PR.request\_date}$) | DateTime | Non-unique | RFQ broadcast date. |
| `submission_deadline` | STRING | Required | ISO-8601 Timestamp ($> \text{issue\_date}$) | DateTime | Non-unique | Quote submission cutoff. |
| `status` | ENUM | Required | `OPEN`, `EVALUATING`, `AWARDED`, `CANCELLED`, `EXPIRED` | N/A | Non-unique | Sourcing stage. |
| `target_currency` | ENUM | Required | `USD` | ISO-4217 | Non-unique | Base evaluation currency. |
| `min_quotes_required` | INTEGER | Required | Integer $\ge 3$ for competitive bids | Count | Non-unique | Competitive governance minimum. |
| `quotes_received_count` | INTEGER | Required | Integer $\ge 0$ | Count | Non-unique | Number of bids submitted. |
| `award_date` | STRING | Optional | ISO-8601 Date ($\ge \text{submission\_deadline}$) | Date | Non-unique | Selection award date. |
| `awarded_supplier_id` | STRING | Optional | FK -> `suppliers.supplier_id` | ID | Foreign Key | Winning vendor ID. |
| `awarded_quote_id` | STRING | Optional | FK -> `supplier_quotes.quote_id` | ID | Foreign Key | Winning quote ID. |

---

## 8. Supplier Quote (`supplier_quotes`)
Vendor bid submitted in response to an RFQ with total landed cost components.

| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule & Business Logic |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `quote_id` | STRING | Required | `QUO-<supplier-code>-2026-\d{6}` | ID | Primary Key | Standardized quote identifier. |
| `rfq_id` | STRING | Required | FK -> `rfqs.rfq_id` | ID | Foreign Key | Parent RFQ. |
| `supplier_id` | STRING | Required | FK -> `suppliers.supplier_id` | ID | Foreign Key | Quoting supplier. |
| `quote_date` | STRING | Required | ISO-8601 Date | Date | Non-unique | Submission date. |
| `validity_end_date` | STRING | Required | ISO-8601 Date ($\ge \text{quote\_date}$) | Date | Non-unique | Price expiration date. Must be $\ge \text{RFQ.award\_date}$. |
| `currency` | ENUM | Required | `USD`, `EUR`, `GBP`, `CAD` | ISO-4217 | Non-unique | Billing currency. |
| `exchange_rate_to_usd` | FLOAT | Required | Float $> 0.0$ (1.0 for USD, 1.08 for EUR, etc.) | Ratio | Non-unique | Currency conversion rate. |
| `base_amount` | FLOAT | Required | Real number $\ge 0.0$ | Quote Curr | Non-unique | Must equal exact sum of `quote_lines`. |
| `freight_cost` | FLOAT | Required | Real number $\ge 0.0$ | Quote Curr | Non-unique | Freight & logistics cost. |
| `tax_duty_amount` | FLOAT | Required | Real number $\ge 0.0$ | Quote Curr | Non-unique | Import tariffs / taxes. |
| `discount_amount` | FLOAT | Required | Real number $\ge 0.0$ | Quote Curr | Non-unique | Offered discount. |
| `total_landed_cost_usd` | FLOAT | Required | Calculated landed cost in USD | USD | Non-unique | $(\text{base} - \text{discount} + \text{freight} + \text{duty}) \times \text{exchange\_rate}$. |
| `promised_lead_time_days` | INTEGER | Required | Integer $\ge 1$ | Days | Non-unique | Calendar days from PO to delivery. |
| `payment_terms` | ENUM | Required | Same as `PaymentTerms` | N/A | Non-unique | Offered terms. |
| `warranty_months` | INTEGER | Required | Integer $\ge 0$ | Months | Non-unique | Warranty coverage. |
| `quote_status` | ENUM | Required | `SUBMITTED`, `UNDER_REVIEW`, `ACCEPTED`, `REJECTED`, `EXPIRED` | N/A | Non-unique | Disposition status. |
| `landed_cost_rank` | INTEGER | Required | Integer $\ge 1$ | Rank | Non-unique | 1 = lowest total landed cost. |
| `selection_score` | FLOAT | Required | Real number $0.00 \le \text{score} \le 100.00$ | Score | Non-unique | Multi-criteria score (Cost, Lead Time, Quality). |
| `award_rationale` | STRING | Optional | Text explanation | N/A | Non-unique | Mandatory if awarded quote is not lowest cost. |

---

## 9. Quote Line (`quote_lines`)
Line item pricing within a supplier quote.

| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule & Business Logic |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `quote_line_id` | STRING | Required | `<quote_id>-L\d{2}` | ID | Primary Key | Unique line ID. |
| `quote_id` | STRING | Required | FK -> `supplier_quotes.quote_id` | ID | Foreign Key | Parent quote ID. |
| `line_number` | INTEGER | Required | Sequential integer $\ge 1$ | Index | Non-unique | Corresponds to PR line number. |
| `item_description` | STRING | Required | Item description | N/A | Non-unique | Description of quoted item. |
| `quantity` | INTEGER | Required | Integer $> 0$ | Count | Non-unique | Quantity quoted. |
| `unit_price` | FLOAT | Required | Real number $> 0.0$ | Quote Curr | Non-unique | Price per unit. |
| `line_total` | FLOAT | Required | Calculated: `quantity * unit_price` | Quote Curr | Non-unique | Line total. |

---

## 10. Approval (`approvals`)
Auditable record of a signing decision made against a PR or PO.

| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule & Business Logic |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `approval_id` | STRING | Required | `APP-2026-\d{6}` | ID | Primary Key | Immutable approval event ID. |
| `entity_type` | STRING | Required | `PURCHASE_REQUEST`, `PURCHASE_ORDER` | Type | Non-unique | Entity under evaluation. |
| `entity_id` | STRING | Required | Target entity ID | ID | Non-unique | FK to PR or PO. |
| `tier_level` | ENUM | Required | Same as `ApprovalTier` | N/A | Non-unique | Evaluated authority tier. |
| `approver_id` | STRING | Required | FK -> `requesters.requester_id` | ID | Foreign Key | Employee rendering decision. |
| `decision` | ENUM | Required | `APPROVED`, `REJECTED`, `DELEGATED`, `SYSTEM_OVERRIDE` | N/A | Non-unique | Formal outcome. |
| `decision_date` | STRING | Required | ISO-8601 Timestamp | DateTime | Non-unique | Decision timestamp. |
| `amount_evaluated` | FLOAT | Required | Real number $\ge 0.0$ | USD | Non-unique | Financial commitment amount. |
| `approver_limit_at_decision` | FLOAT | Required | Real number $\ge 0.0$ | USD | Non-unique | Approver signing limit. Must be $\ge \text{amount}$ (unless override). |
| `comments` | STRING | Optional | Text justification | N/A | Non-unique | Audit explanation or rejection reason. |
| `is_override` | BOOLEAN | Required | `TRUE`, `FALSE` | Flag | Non-unique | Emergency or executive exception flag. |

---

## 11. Purchase Order (`purchase_orders`)
Legally binding commercial order issued to an awarded supplier.

| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule & Business Logic |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `po_id` | STRING | Required | `PO-2026-\d{6}` (e.g. `PO-2026-000001`) | ID | Primary Key | Immutable Purchase Order identifier. |
| `request_id` | STRING | Required | FK -> `purchase_requests.request_id` | ID | Foreign Key | Originating PR ID. |
| `rfq_id` | STRING | Optional | FK -> `rfqs.rfq_id` | ID | Foreign Key | Sourcing RFQ (if competitive). |
| `quote_id` | STRING | Optional | FK -> `supplier_quotes.quote_id` | ID | Foreign Key | Awarded quote ID. |
| `supplier_id` | STRING | Required | FK -> `suppliers.supplier_id` | ID | Foreign Key | Contracted vendor. Must be active. |
| `po_date` | STRING | Required | ISO-8601 Date ($\ge \text{PR/award date}$) | Date | Non-unique | Issue date of purchase order. |
| `required_delivery_date` | STRING | Required | ISO-8601 Date ($> \text{po\_date}$) | Date | Non-unique | Contractual delivery target. |
| `status` | ENUM | Required | `ISSUED`, `ACKNOWLEDGED`, `PARTIALLY_DELIVERED`, `FULFILLED`, `CANCELLED`, `CLOSED` | N/A | Non-unique | Order lifecycle status. |
| `currency` | ENUM | Required | `USD` | ISO-4217 | Non-unique | PO transaction currency. |
| `total_po_amount` | FLOAT | Required | Real number $\ge 0.0$ | USD | Non-unique | Must equal exact sum of `po_lines`. |
| `payment_terms` | ENUM | Required | Same as `PaymentTerms` | N/A | Non-unique | Contract payment terms. |
| `delivery_address` | STRING | Required | Corporate destination address | N/A | Non-unique | Physical receiving dock destination. |
| `approval_reference_id` | STRING | Optional | FK -> `approvals.approval_id` | ID | Foreign Key | Required for valid issuance. NULL triggers `PO_WITHOUT_APPROVAL` anomaly. |

---

## 12. PO Line (`po_lines`)
Individual line item in a Purchase Order.

| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule & Business Logic |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `po_line_id` | STRING | Required | `PO-2026-\d{6}-L\d{2}` | ID | Primary Key | Unique PO line identifier. |
| `po_id` | STRING | Required | FK -> `purchase_orders.po_id` | ID | Foreign Key | Parent PO ID. |
| `line_number` | INTEGER | Required | Sequential integer $\ge 1$ | Index | Non-unique | Line sequence number. |
| `item_description` | STRING | Required | Item description text | N/A | Non-unique | Description matching quote line. |
| `quantity_ordered` | INTEGER | Required | Integer $> 0$ | Count | Non-unique | Number of units purchased. |
| `unit_price` | FLOAT | Required | Real number $> 0.0$ | USD | Non-unique | Unit price in USD. |
| `line_amount` | FLOAT | Required | Calculated: `quantity_ordered * unit_price` | USD | Non-unique | Total line financial value. |
| `quantity_received` | INTEGER | Required | Integer $\ge 0$ | Count | Non-unique | Cumulative received quantity from deliveries. |

---

## 13. Delivery (`deliveries`)
Inbound logistics delivery event and receiving inspection.

| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule & Business Logic |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `delivery_id` | STRING | Required | `DEL-PO-2026-\d{6}-\d{2}` | ID | Primary Key | Standard delivery event ID. |
| `po_id` | STRING | Required | FK -> `purchase_orders.po_id` | ID | Foreign Key | Target Purchase Order. |
| `shipment_number` | INTEGER | Required | Sequential integer $\ge 1$ | Index | Non-unique | Shipment sequence (1 for full, 1 & 2 for partial). |
| `delivery_date` | STRING | Required | ISO-8601 Date ($\ge \text{PO.po\_date}$) | Date | Non-unique | Physical receiving date. |
| `carrier` | ENUM | Required | `FEDEX`, `UPS`, `DHL`, `FREIGHT_DIRECT`, `MAERSK` | N/A | Non-unique | Logistics carrier. |
| `tracking_number` | STRING | Required | Carrier tracking code | Code | Non-unique | Proof of transit. |
| `delivery_status` | ENUM | Required | `IN_TRANSIT`, `DELIVERED_ON_TIME`, `DELIVERED_LATE`, `DAMAGED`, `REJECTED` | N/A | Non-unique | Physical arrival outcome. |
| `received_by_user_id` | STRING | Required | FK -> `requesters.requester_id` | ID | Foreign Key | Receiving dock staff who signed. |
| `inspection_status` | ENUM | Required | `PASSED`, `FAILED`, `PENDING_INSPECTION`, `ACCEPTED_WITH_CONCESSION` | N/A | Non-unique | Receiving quality audit. |
| `items_delivered_count` | INTEGER | Required | Integer $\ge 0$ | Count | Non-unique | Quantity verified in this shipment. |
| `is_partial` | BOOLEAN | Required | `TRUE`, `FALSE` | Flag | Non-unique | Partial fulfillment indicator. |
| `notes` | STRING | Optional | Receiving notes | N/A | Non-unique | Inspection comments or discrepancy notes. |

---

## 14. Audit Event (`audit_events`)
Immutable event log persisting every lifecycle state transition.

| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule & Business Logic |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `event_id` | STRING | Required | `EVT-\d{8}` (e.g. `EVT-00000001`) | ID | Primary Key | Immutable sequential audit event ID. |
| `entity_type` | STRING | Required | `PURCHASE_REQUEST`, `RFQ`, `SUPPLIER_QUOTE`, `PURCHASE_ORDER`, `DELIVERY`, `BUDGET` | Type | Non-unique | Entity type modified. |
| `entity_id` | STRING | Required | Primary key of subject entity | ID | Non-unique | Target entity identifier. |
| `event_timestamp` | STRING | Required | ISO-8601 Timestamp | DateTime | Non-unique | Exact wall-clock event time. |
| `actor_id` | STRING | Required | Requester ID or `SYSTEM` | ID | Non-unique | Actor who performed the action. |
| `previous_state` | STRING | Optional | Status before action or `NULL` | State | Non-unique | Previous lifecycle state. |
| `new_state` | STRING | Required | Status after action | State | Non-unique | Transitioned lifecycle state. |
| `action_type` | STRING | Required | `REQUEST_SUBMITTED`, `APPROVAL_DECISION`, `AWARD_SUPPLIER`, `PO_ISSUED`, `DELIVERY_RECORDED` | Action | Non-unique | Classification of action taken. |
| `details` | STRING | Required | Narrative audit trail text | N/A | Non-unique | Human-readable audit narrative. |

---

## 15. Ground Truth (`ground_truth`)
Isolated governance and evaluation table storing all injected anomalies and expected auditor verdicts.

| Field Name | Type | Req/Opt | Allowed Values / Format | Units | Uniqueness | Validation Rule & Business Logic |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `anomaly_id` | STRING | Required | `ANO-\d{5}` (e.g. `ANO-00001`) | ID | Primary Key | Immutable anomaly label identifier. |
| `entity_type` | STRING | Required | `PurchaseOrder`, `SupplierQuote`, `Budget`, `PurchaseRequest`, `Supplier` | Type | Non-unique | Entity containing the injected anomaly. |
| `entity_id` | STRING | Required | Foreign entity ID | ID | Non-unique | Target record primary key. |
| `issue_type` | ENUM | Required | `PO_WITHOUT_APPROVAL`, `QUOTE_EXPIRED_BEFORE_AWARD`, `NON_CHEAPEST_WITHOUT_RATIONALE`, `INACTIVE_SUPPLIER`, `BUDGET_OVERRUN`, `DUPLICATE_REQUEST`, `QUOTE_CURRENCY_MISMATCH`, `SPLIT_PURCHASE` | Type | Non-unique | Exact anomaly classification. |
| `severity` | ENUM | Required | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` | N/A | Non-unique | Business risk severity. |
| `rule_violated` | STRING | Required | Rule Code & Name (e.g. `BR-001`) | Rule | Non-unique | Governance policy breached. |
| `description` | STRING | Required | Narrative explanation of violation | N/A | Non-unique | Explanatory description. |
| `detection_criteria` | STRING | Required | Algorithmic logic statement | Logic | Non-unique | Algorithmic rule for automated detection. |
| `injected_at_stage` | STRING | Required | Workflow stage | Stage | Non-unique | Lifecycle stage where anomaly was created. |
| `expected_audit_verdict` | STRING | Required | `NON_COMPLIANT`, `FLAGGED_FOR_REVIEW` | Verdict | Non-unique | Expected determination by audit engine. |

