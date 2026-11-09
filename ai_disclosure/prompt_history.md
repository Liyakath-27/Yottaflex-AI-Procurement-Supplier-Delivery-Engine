# Yottaflex AI Recruitment Drive — Prompt History Log

**Candidate Role**: Associate AI Forward Deployed Engineer  
**Challenge**: Round 2: 72 Hours Code Challenge  
**Evaluation Window**: 72 Hours (Ending Mon 9 Nov 2026, 14:55 UTC)  
**Tools Used**: Google Antigravity (Gemini 3.8 Flash High)  

---

## Prompt 1: Initial Problem Statement & Specification Submission

**Submitted At**: `2026-11-09T07:54:47+05:30`  
**Target Tool**: AI Assistant (Antigravity)

```text
Business Context / Problem
Manage purchase requests, quote comparisons, approvals, purchase orders and supplier delivery.

Objective and Scope
Build a working solution for this end-to-end workflow: Manage purchase requests, quote comparisons, approvals, purchase orders and supplier delivery. The solution should expose key decisions and exceptions, preserve traceability, and produce measurable outputs. Medium complexity means multiple related entities, conditional rules, at least one exception path and meaningful evaluation metrics.

Primary Actors / Systems
Business requester, process owner, approver, operations analyst and system administrator

Business Workflow and Rules
1. Generate/reference master data first: Requester, Department, Budget, PurchaseRequest, RequestLine.
2. Generate dependent transaction/event records using valid parent IDs.
3. Apply business logic: Create departments and budgets; create requests with item/category/quantity and estimated cost; apply approval thresholds; create RFQs for eligible requests; capture at least three supplier quotes for competitive purchases; compare total landed cost and delivery time; award supplier; generate PO lines from approved quote; create delivery events.
4. Persist state changes as explicit records/events where relevant; do not overwrite history.
5. Generate outcomes and ground-truth labels from documented rules, not independent random assignment.

Entities and Relationships
Core entities: Requester, Department, Budget, PurchaseRequest, RequestLine, Supplier, RFQ, SupplierQuote, Approval, PurchaseOrder, Delivery. Define a primary key for every entity and foreign keys for every relationship. Document cardinality (1:1, 1:N, N:M), optional relationships, effective dates and lifecycle states. Use bridge tables for many-to-many relationships; retain event history for state changes; validate all joins. For deliberate anomaly cases, keep an issue_type/ground_truth label rather than silently corrupting unrelated rows.

ID / Nomenclature Conventions
PR-2026-000001; RFQ-2026-000001; QUO-<supplier-code>-2026-000001; PO-2026-000001; DEL-<PO-id>-01.

Synthetic Data Generation Instructions (Granular)
Step 1 — Write a data dictionary for: Requester, Department, Budget, PurchaseRequest, RequestLine, Supplier, RFQ, SupplierQuote, Approval, PurchaseOrder, Delivery. For each field specify type, required/optional, allowed values, units, uniqueness and validation rule.
Step 2 — Create parent/master tables first, then child and event tables. Apply this domain-specific generation logic: Create departments and budgets; create requests with item/category/quantity and estimated cost; apply approval thresholds; create RFQs for eligible requests; capture at least three supplier quotes for competitive purchases; compare total landed cost and delivery time; award supplier; generate PO lines from approved quote; create delivery events.
Step 3 — Apply deterministic IDs and naming: PR-2026-000001; RFQ-2026-000001; QUO-<supplier-code>-2026-000001; PO-2026-000001; DEL-<PO-id>-01. Keep counters zero-padded, IDs immutable, and referenced IDs exactly consistent across files.
Step 4 — Generate the baseline volume: Generate 300 requesters, 120 suppliers, 1,200 requests, 500 RFQs, 1,500 quotes and 900 POs. Include single-source exceptions, over-budget requests, split purchases, quote expiry, supplier risk flags and partial deliveries. Use a fixed seed (e.g. 20261022) and parameterize scale so starter and full datasets use the same generator.
Step 5 — Generate valid baseline records first, then inject labelled edge cases: PO issued without approval; quote expired before award; selected quote not cheapest without documented rationale; supplier inactive; budget overrun; duplicate request; quote currency mismatch.
Step 6 — Calculate derived values (totals, balances, scores, statuses and dates) from source records rather than generating them independently.
Step 7 — Produce a separate ground_truth.csv/json for known anomalies, expected decisions or labels; never leak it into input features.
Step 8 — Run validation: primary-key uniqueness, foreign-key integrity, allowed enums, date ordering, arithmetic reconciliation, lifecycle transitions and duplicate checks.
Step 9 — Export CSV/JSON/SQL seed data plus README, schema/data dictionary, generator command, fixed seed, source manifest and validation summary.
Step 10 — Regenerate twice with the same seed and compare row counts/checksums to demonstrate reproducibility.

Suggested Volume and Coverage
Generate 300 requesters, 120 suppliers, 1,200 requests, 500 RFQs, 1,500 quotes and 900 POs. Include single-source exceptions, over-budget requests, split purchases, quote expiry, supplier risk flags and partial deliveries.

Required Edge Cases / Negative Scenarios
PO issued without approval; quote expired before award; selected quote not cheapest without documented rationale; supplier inactive; budget overrun; duplicate request; quote currency mismatch.

Validation Rules / Acceptance Criteria
Approval thresholds enforced; supplier selection is explainable; PO values equal awarded quote lines; budget reservation is consistent; every exception has a reason and audit trail.

Evaluation Focus for Generated Data
Review: (a) realistic distributions and meaningful variation; (b) consistent IDs and valid joins; (c) dependency/lifecycle consistency across entities; (d) correct derived values and reconciliation; (e) normal, boundary, failure and exception coverage; (f) separate ground truth; (g) fixed-seed reproducibility, documentation and lawful provenance.

Public Data Guidance / Lawful Use
External data is optional. If used, record source URL, dataset/version, retrieval date, license/terms, attribution, transformations and fields discarded. Use only data you are legally permitted to access and redistribute; do not bypass access controls or collect confidential/personal information. If licensing or suitability is unclear, use synthetic data and cite public reference data only for schema inspiration.
```

---

## Prompt 2: Operational Commands and Output Request

**Submitted At**: `2026-11-09T08:18:06+05:30`  
**Target Tool**: AI Assistant (Antigravity)

```text
commands to run and see output
```

---

## Prompt 3: FAQ and Submission Guidelines Clarification

**Submitted At**: `2026-11-09T08:23:21+05:30`  
**Target Tool**: AI Assistant (Antigravity)

```text
[Yottaflex AI Recruitment Drive Candidate Project FAQ and Submission Guidelines text shared to align submission structure with public repository, transparency, and explanation requirements.]
```

