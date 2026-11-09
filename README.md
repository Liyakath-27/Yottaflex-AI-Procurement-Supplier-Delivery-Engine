# Yottaflex Enterprise Procurement & Supplier Delivery Engine

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Validation Status](https://img.shields.io/badge/validation-37%20passed%20%2F%200%20failed-success.svg)](reports/validation_summary.md)
[![Audit Accuracy](https://img.shields.io/badge/audit%20F1--score-99.63%25-brightgreen.svg)](reports/validation_summary.md)
[![Reproducibility](https://img.shields.io/badge/reproducibility-100%25%20bitwise%20match-blueviolet.svg)](tests/test_reproducibility.py)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

An end-to-end, auditable enterprise workflow platform that automates and governs:
1. **Purchase Request Creation & Multi-Tier Approvals** (authority thresholds, budget reservations, separation of duties).
2. **Competitive Sourcing & RFQ Dispatch** (mandating $\ge 3$ supplier quotes for competitive bids).
3. **Total Landed Cost Evaluation & Supplier Award** (normalizing freight, duties, discounts, FX rates, lead times, and multi-criteria scoring).
4. **Purchase Order Issuance & PO Line Synchronization** (exact parity with awarded quote lines).
5. **Inbound Logistics & Delivery Inspection** (on-time, late, partial deliveries, and receiving quality inspections).
6. **Immutable State Transition History & Governance Auditing** (auditing rule compliance against ground truth).

---

## 1. Quick Start

### Installation
Clone or navigate to the workspace directory. Standard library plus `pydantic` and `fastapi` are utilized:
```powershell
pip install pydantic fastapi uvicorn click
```

### Run Full Verification Suite
Executes relational validation, audit accuracy benchmark, and bitwise reproducibility test in one command:
```powershell
python run_tests.py
```

### CLI Command Suite
The unified CLI tool `src/cli.py` exposes all lifecycle capabilities:

```powershell
# 1. Generate full target dataset with fixed seed 20261022
python -m src.cli generate --scale full --seed 20261022 --outdir data

# 2. Run full 37-point validation suite on generated data
python -m src.cli validate --scale full --seed 20261022

# 3. Test bitwise reproducibility across two independent runs
python -m src.cli reproduce --scale starter --seed 20261022

# 4. Launch interactive Web Dashboard and REST API
python -m src.cli serve --host 127.0.0.1 --port 8000
```

---

## 2. Primary Actors & System Roles

| Primary Actor | System Responsibilities |
| :--- | :--- |
| **Business Requester** | Submits itemized Purchase Requests (`PR`), specifies urgency, delivery location, and single-source justifications. |
| **Process Owner (Procurement)** | Issues RFQs, gathers vendor bids, evaluates Total Landed Cost, records award rationales, and generates POs. |
| **Approver (Manager / Director / VP)** | Reviews requests against financial authority thresholds ($<\$1\text{K}$, $\$10\text{K}$, $\$50\text{K}$, $\$50\text{K}+$); approves or rejects with audit comments. |
| **Operations Analyst (Logistics)** | Records carrier shipments, tracking numbers, on-time vs delayed receipts, partial shipments, and receiving inspection passes/concessions. |
| **System Administrator / Auditor** | Scans compliance against rules (BR-001 through BR-008), benchmarks detection against `ground_truth.csv`, and tracks budget encumbrance. |

---

## 3. Data Dictionary & Entity Model

The solution defines 15 core entities and event tables:
1. [`departments`](docs/data_dictionary.md#1-department-departments) — Organizational units & cost centers.
2. [`budgets`](docs/data_dictionary.md#2-budget-budgets) — Annual categorical budget limits and encumbrances.
3. [`requesters`](docs/data_dictionary.md#3-requester-requesters) — Employees across 7 signing authority tiers.
4. [`suppliers`](docs/data_dictionary.md#4-supplier-suppliers) — Commercial vendors with performance and risk ratings.
5. [`purchase_requests`](docs/data_dictionary.md#5-purchase-request-purchase_requests) — Request headers with routing tiers.
6. [`request_lines`](docs/data_dictionary.md#6-request-line-request_lines) — Itemized quantities, unit estimates, and line totals.
7. [`rfqs`](docs/data_dictionary.md#7-rfq-rfqs) — Sourcing bids with deadline and award targets.
8. [`supplier_quotes`](docs/data_dictionary.md#8-supplier-quote-supplier_quotes) — Vendor proposals with landed cost breakdowns.
9. [`quote_lines`](docs/data_dictionary.md#9-quote-line-quote_lines) — Itemized quote line pricing.
10. [`approvals`](docs/data_dictionary.md#10-approval-approvals) — Auditable signing decisions and authority limits.
11. [`purchase_orders`](docs/data_dictionary.md#11-purchase-order-purchase_orders) — Binding commercial orders.
12. [`po_lines`](docs/data_dictionary.md#12-po-line-po_lines) — PO line items matching awarded quote lines.
13. [`deliveries`](docs/data_dictionary.md#13-delivery-deliveries) — Inbound shipments, carrier tracking, and inspection outcomes.
14. [`audit_events`](docs/data_dictionary.md#14-audit-event-audit_events) — Immutable event log persisting every state change.
15. [`ground_truth`](docs/data_dictionary.md#15-ground-truth-ground_truth) — Isolated labelled anomalies and expected audit verdicts.

👉 **Full Schema & Field Specifications**: See [docs/data_dictionary.md](docs/data_dictionary.md)  
👉 **Architecture & ER Diagram**: See [docs/workflow_architecture.md](docs/workflow_architecture.md)  
👉 **Business Governance Rules**: See [docs/business_rules.md](docs/business_rules.md)  

---

## 4. Deterministic ID & Nomenclature Conventions

Counters are zero-padded, IDs are immutable, and referenced IDs are strictly consistent across files:
- **Purchase Request**: `PR-2026-000001` .. `PR-2026-001224`
- **Request Line**: `PR-2026-000001-L01`, `PR-2026-000001-L02`
- **RFQ**: `RFQ-2026-000001` .. `RFQ-2026-000500`
- **Supplier Quote**: `QUO-<supplier-code>-2026-000001` (e.g. `QUO-APEX01-2026-000001`)
- **Quote Line**: `QUO-APEX01-2026-000001-L01`
- **Purchase Order**: `PO-2026-000001` .. `PO-2026-000900`
- **PO Line**: `PO-2026-000001-L01`
- **Delivery Event**: `DEL-<PO-id>-01` (e.g. `DEL-PO-2026-000001-01` for full, `01` & `02` for partial)
- **Approval**: `APP-2026-000001` .. `APP-2026-001200`
- **Audit Event**: `EVT-00000001` .. `EVT-00004300`
- **Ground Truth**: `ANO-00001` .. `ANO-000135`

---

## 5. Dataset Volume & Coverage

The generator supports parameterized scale (`--scale starter` vs `--scale full`). The full scale satisfies and exceeds target coverage requirements:

| Entity | Baseline Target | Generated (Full) | Generated (Starter) | Coverage Highlights |
| :--- | :--- | :--- | :--- | :--- |
| **Requesters** | 300 | **300** | 30 | 7 Roles from Junior Analyst to VP |
| **Suppliers** | 120 | **120** | 15 | Active & inactive, domestic & international FX |
| **Purchase Requests** | 1,200 | **1,224** | 124 | 1,200 standard + 24 injected duplicates |
| **RFQs** | 500 | **500** | 50 | 100% of competitive bids $\ge \$2,500$ |
| **Supplier Quotes** | 1,500 | **1,500** | 150 | $\ge 3$ competitive quotes per RFQ |
| **Purchase Orders** | 900 | **900** | 90 | PO lines match quote lines exactly |
| **Inbound Deliveries** | ~900 | **952** | 96 | On-time (80%), late (12%), partial (6%), damaged (2%) |
| **Audit Events** | Event Log | **4,300** | 430 | Every state transition preserved |
| **Ground Truth Anomalies**| Isolated | **135** | 44 | Isolated in `ground_truth.csv`/`json` |

---

## 6. Labelled Edge Cases & Governance Rules

All anomalies are generated deterministically and labelled in `ground_truth.csv` and `ground_truth.json` without leaking into standard feature columns:

| Issue Type | Governance Rule | Severity | Detection Logic | Auditor Recall |
| :--- | :--- | :--- | :--- | :--- |
| `PO_WITHOUT_APPROVAL` | BR-001 | `CRITICAL` | `PO.approval_reference_id IS NULL` | **100.0%** (18/18) |
| `QUOTE_EXPIRED_BEFORE_AWARD` | BR-002 | `HIGH` | `Quote.validity_end_date < RFQ.award_date` | **100.0%** (12/12) |
| `NON_CHEAPEST_WITHOUT_RATIONALE` | BR-003 | `HIGH` | Awarded non-lowest quote with empty rationale | **100.0%** (15/15) |
| `INACTIVE_SUPPLIER` | BR-004 | `CRITICAL` | PO or quote issued to supplier with `is_active = FALSE` | **100.0%** (48/48) |
| `BUDGET_OVERRUN` | BR-005 | `HIGH` | Committed + spent exceeds allocated budget ceiling | **100.0%** (4/4) |
| `DUPLICATE_REQUEST` | BR-006 | `MEDIUM` | Identical item & quantity signature submitted $\le 72\text{h}$ | **100.0%** (24/24) |
| `QUOTE_CURRENCY_MISMATCH` | BR-007 | `HIGH` | Foreign currency (EUR/GBP) quote entered as 1:1 USD without FX | **92.86%** (13/14) |

---

## 7. Exported Artifacts

The system exports all datasets in 4 standard enterprise formats in `data/`:
- `data/csv/*.csv`: 14 Operational entity CSVs + `ground_truth.csv`.
- `data/json/*.json`: 14 Operational entity JSONs + `ground_truth.json`.
- `data/procurement.db`: Fully populated relational SQLite database with indexes.
- `data/sql/schema.sql`: Standard SQL DDL creating all tables and foreign keys.
- `data/sql/seed_data.sql`: Standard SQL `INSERT` statements for all records (6.1 MB).
- `data/manifest.json`: Cryptographic source manifest containing SHA256 checksums, row counts, parameters, and provenance metadata.

---

## 8. Lawful Use & Synthetic Provenance Statement

- **Lawful Use Classification**: 100% Synthetic Domain-Generated Data.
- **Personal Data**: Contains zero Personally Identifiable Information (PII). All employee and vendor names were generated from synthetic pools.
- **Commercial Confidentiality**: No confidential company data was ingested or extracted.
- **License**: MIT / Creative Commons Zero (CC0). Permitted for open commercial and research use.

