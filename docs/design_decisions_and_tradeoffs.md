# Architectural Design Decisions, Assumptions & Trade-offs

**Role**: Associate AI Forward Deployed Engineer  
**Requirement**: 04 MAKE YOUR REASONING VISIBLE — EXPLAIN THE WHY  

---

## 1. Problem Framing & Core Objectives
In enterprise supply chains and procurement operations, financial loss and regulatory non-compliance typically stem from three failure modes:
1. **Approval Evasion**: Split purchases and missing sign-offs bypassing authority limits.
2. **Opaque Sourcing**: Inability to mathematically reconcile why a particular supplier was awarded over lower bidders.
3. **Audit Trail Degradation**: Overwriting database status in-place without preserving state transition history.

The objective of this solution is to build a mathematically verifiable, relational procurement engine that enforces governance rules, calculates total landed cost, persists an immutable audit trail, and isolates ground-truth failure modes for auditor benchmarking.

---

## 2. Key Architectural Decisions

### A. Normalized Relational Schema vs Document Store
- **Decision**: Implemented a normalized 15-entity relational architecture with explicit foreign keys and bridge tables in SQLite and standard SQL.
- **Trade-off**: Requires more joins and schema rigour during generation compared to unstructured JSON document stores.
- **Why**: Procurement is strictly relational; PO amounts must equal awarded quote lines, and delivery items received must reconcile against ordered quantities. Referential integrity guarantees that orphaned records or corrupt relationships are physically impossible.

### B. Isolated Ground Truth vs In-Place Anomaly Flagging
- **Decision**: Injected anomalies (`PO_WITHOUT_APPROVAL`, `QUOTE_EXPIRED_BEFORE_AWARD`, `NON_CHEAPEST_WITHOUT_RATIONALE`, `INACTIVE_SUPPLIER`, `BUDGET_OVERRUN`, `DUPLICATE_REQUEST`, `QUOTE_CURRENCY_MISMATCH`, `SPLIT_PURCHASE`) are stored in a dedicated `ground_truth` table, completely isolated from operational tables.
- **Trade-off**: Requires maintaining a separate ground-truth mapping mechanism and secondary indexing.
- **Why**: In real-world enterprise AI evaluation, labelling anomalies inside operational tables causes feature leakage. An auditor or machine learning classifier must infer violations purely from standard business features.

### C. Total Landed Cost (TLC) Model vs Nominal Unit Pricing
- **Decision**: Normalized all bids to USD using:
  $$\text{TLC} = (\text{Base} - \text{Discount} + \text{Freight} + \text{Tariffs}) \times \text{Exchange Rate}$$
- **Trade-off**: Increased arithmetic complexity across multi-currency supplier quotes.
- **Why**: Comparing international suppliers on nominal unit price alone is misleading. A supplier with lower base price in EUR may incur higher shipping tariffs and FX markups, making their landed cost significantly higher.

### D. Multi-Attribute Sourcing Score (Cost, Velocity, Reputation)
- **Decision**: Implemented a 100-point composite scoring model:
  - 50% Total Landed Cost (relative to lowest bid)
  - 25% Promised Delivery Velocity (calendar days)
  - 25% Supplier Historical Quality & Performance Rating
- **Why**: Lowest-cost supplier is not always the best choice if their lead time is 45 days and quality rating is poor. If a higher-cost quote is awarded, the system generates an auditable rationale explaining the trade-off. If awarded without rationale, it triggers `NON_CHEAPEST_WITHOUT_RATIONALE`.

---

## 3. Assumptions & Scoping Choices

1. **Fiscal Horizon**: The synthetic generation scope is calibrated for Fiscal Year 2026.
2. **Separation of Duties**: Requesters are prohibited from approving their own purchase requests. If a department lacks an approver with adequate authority limit, the request automatically escalates to the global pool (Directors, VPs).
3. **Competitive Threshold**: Any requirement exceeding $\$2,500.00$ requires competitive sourcing with at least 3 valid supplier quotes, unless explicitly approved as a single-source exception.
4. **Delivery Outcomes**: Calibrated to reflect realistic industrial distributions:
   - 80% On-Time Complete Delivery
   - 12% Carrier Transit Delay
   - 6% Partial Deliveries (shipped in 2 sequential batches)
   - 2% Packaging Damage with Quality Concession Acceptance

---

## 4. How We Know the Solution Works

1. **Automated Validation Suite (`test_validation.py`)**:
   - 37 automated assertions verifying 100% primary key uniqueness, foreign key integrity, allowed enums, date ordering, and line-to-header math reconciliations.
2. **Audit Engine Benchmark (`test_audit_engine.py`)**:
   - An independent rule-based `ProcurementAuditor` scanned all records and achieved **100.00% precision, 99.26% recall, and 99.63% F1-score** across all injected anomalies.
3. **Cryptographic Bitwise Reproducibility (`test_reproducibility.py`)**:
   - Executing two independent generation runs with seed `20261022` produced identical SHA256 hashes across all 33 exported files.

