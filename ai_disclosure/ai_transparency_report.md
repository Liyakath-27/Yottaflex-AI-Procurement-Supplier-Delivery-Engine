# AI Transparency & Human Validation Report

**Candidate Role**: Associate AI Forward Deployed Engineer  
**Submission Requirement**: 03 USE LLMs TRANSPARENTLY  

---

## 1. Overview of AI Assistance
In compliance with the Yottaflex AI Candidate Project Guidelines, this document transparently describes how LLM assistance was integrated into the engineering workflow, where it provided acceleration, where it was relied upon heavily, and what was personally inspected, debugged, and validated.

---

## 2. Where AI Accelerated the Build
1. **Schema & Data Dictionary Scaffolding**:
   - Rapid generation of the 15-entity relational structure and Pydantic models.
   - Initial drafting of SQL DDL (`schema.sql`) and DML insert logic.
2. **Domain Master Data Synthesis**:
   - Constructing realistic item catalogues across 7 expenditure categories (`HARDWARE`, `SOFTWARE`, `SERVICES`, `FACILITIES`, `OFFICE_SUPPLIES`, `CONSULTING`, `LOGISTICS`).
   - Generating believable commercial supplier profiles with historical delivery velocity and quality pass rates.
3. **Validation Test Suite Automation**:
   - Scaffolding the 37 distinct validation assertions (uniqueness, referential integrity, chronology, line-to-header math reconciliation).

---

## 3. Where Heavy Reliance was Placed on AI
1. **Multi-Attribute Sourcing Algorithm Drafting**:
   - Formalizing the mathematical weighting for the 100-point quote selection score:
     $$\text{Score} = 50 \times \left(\frac{\text{Lowest Landed Cost}}{\text{Quote Landed Cost}}\right) + 25 \times \left(\frac{45 - \text{Lead Time}}{45}\right) + \left(\frac{\text{Rating}}{5.0} \times 15 + \text{Quality} \times 10\right)$$
2. **Event Sourcing & State Machine Event Logging**:
   - Synthesizing 4,300 immutable `AuditEvent` transitions matching the lifecycle of each PR, RFQ, PO, and delivery.

---

## 4. What Was Personally Reviewed, Debugged, and Corrected
During development, automated generation revealed several relational and logical edge cases that required hands-on debugging:

1. **Department Requester Allocation in Starter Mode**:
   - *Bug*: In `starter` mode (30 requesters across 10 departments), independent random choice occasionally left a department with 0 requesters, causing department head assignment to throw an `IndexError`.
   - *Fix*: Implemented guaranteed round-robin assignment for the first 10 requesters to ensure every department has at least one active employee before distributing remaining requesters.
2. **QuoteLine Attribute Inconsistency**:
   - *Bug*: Field name mismatch between `line_number` and `rfq_line_number` across Pydantic models and generator functions.
   - *Fix*: Standardized all line item models (`RequestLine`, `QuoteLine`, `POLine`) to consistently use `line_number`.
3. **Disjoint Anomaly Injection Sets for RFQ Awards**:
   - *Bug*: When injecting `QUOTE_EXPIRED_BEFORE_AWARD` and `NON_CHEAPEST_WITHOUT_RATIONALE`, selecting the same RFQ caused the second injection to reassign `awarded_quote_id`, invalidating the first anomaly and reducing auditor recall.
   - *Fix*: Added `self._used_rfq_ids` tracking set in `AnomalyInjector` to guarantee mutually disjoint RFQ candidate pools.
4. **Budget Overrun Boundary Isolation**:
   - *Bug*: Baseline budgets generated in the $350K–$2M range occasionally depleted naturally under heavy purchasing volume, creating unintended budget overruns (false positives).
   - *Fix*: Scaled baseline budgets to $2.5M–$6.0M so that only deliberately injected budgets overrun their allocation, achieving 100% audit precision.
5. **Bitwise Reproducibility Verification**:
   - Personally ran SHA256 directory hashing across two independent generation runs to confirm that Python's pseudo-random number generator state produced zero file diffs across all 33 files.

---

## 5. Conclusion & Ownership
The architecture, separation of duties, threshold governance, and validation methodologies reflect sound systems engineering judgment. The AI tool functioned as a high-speed code accelerator, while system design, constraint enforcement, and verification integrity were actively driven and owned by the candidate.

