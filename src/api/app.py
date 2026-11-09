"""
FastAPI Application and Interactive Procurement Dashboard.
Provides REST endpoints and a responsive Web UI for end-to-end workflow tracing.
"""
import os
import json
import sqlite3
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from src.analytics.metrics import ProcurementMetricsEngine
from src.engine.workflow_simulator import execute_simulated_workflow

app = FastAPI(
    title="Yottaflex Procurement & Supplier Delivery Engine",
    description="End-to-End Enterprise Procurement Workflow, Quote Comparison, and Governance System",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.path.join("data", "procurement.db")


def get_db():
    if not os.path.exists(DB_PATH):
        raise HTTPException(
            status_code=500,
            detail="Database not initialized. Please run `python -m src.cli generate` first.",
        )
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "database_available": os.path.exists(DB_PATH)}


@app.get("/api/stats")
def get_kpis():
    conn = get_db()
    cur = conn.cursor()

    total_prs = cur.execute("SELECT COUNT(*) FROM purchase_requests").fetchone()[0]
    total_rfqs = cur.execute("SELECT COUNT(*) FROM rfqs").fetchone()[0]
    total_quotes = cur.execute("SELECT COUNT(*) FROM supplier_quotes").fetchone()[0]
    total_pos = cur.execute("SELECT COUNT(*) FROM purchase_orders").fetchone()[0]
    total_spend = cur.execute("SELECT COALESCE(SUM(total_po_amount), 0) FROM purchase_orders").fetchone()[0]
    total_anomalies = cur.execute("SELECT COUNT(*) FROM ground_truth").fetchone()[0]
    avg_rating = cur.execute("SELECT COALESCE(AVG(performance_rating), 0) FROM suppliers").fetchone()[0]
    avg_ontime = cur.execute("SELECT COALESCE(AVG(on_time_delivery_rate), 0) FROM suppliers").fetchone()[0]

    conn.close()
    return {
        "total_purchase_requests": total_prs,
        "total_rfqs": total_rfqs,
        "total_supplier_quotes": total_quotes,
        "total_purchase_orders": total_pos,
        "total_committed_po_spend_usd": round(total_spend, 2),
        "total_ground_truth_anomalies": total_anomalies,
        "average_supplier_rating": round(avg_rating, 2),
        "average_supplier_ontime_rate": round(avg_ontime * 100, 1),
    }


@app.get("/api/requests")
def list_requests(limit: int = 50, status: Optional[str] = None):
    conn = get_db()
    cur = conn.cursor()
    query = """
        SELECT pr.*, r.name as requester_name, d.department_name
        FROM purchase_requests pr
        JOIN requesters r ON pr.requester_id = r.requester_id
        JOIN departments d ON pr.department_id = d.department_id
    """
    params = []
    if status:
        query += " WHERE pr.status = ?"
        params.append(status)
    query += " ORDER BY pr.request_date DESC LIMIT ?"
    params.append(limit)

    rows = cur.execute(query, params).fetchall()
    results = [dict(row) for row in rows]
    conn.close()
    return results


@app.get("/api/requests/{request_id}")
def get_request_detail(request_id: str):
    conn = get_db()
    cur = conn.cursor()

    pr = cur.execute(
        """
        SELECT pr.*, r.name as requester_name, d.department_name
        FROM purchase_requests pr
        JOIN requesters r ON pr.requester_id = r.requester_id
        JOIN departments d ON pr.department_id = d.department_id
        WHERE pr.request_id = ?
        """,
        (request_id,),
    ).fetchone()

    if not pr:
        conn.close()
        raise HTTPException(status_code=404, detail="Request not found")

    lines = cur.execute(
        "SELECT * FROM request_lines WHERE request_id = ? ORDER BY line_number",
        (request_id,),
    ).fetchall()

    approvals = cur.execute(
        """
        SELECT a.*, r.name as approver_name
        FROM approvals a
        JOIN requesters r ON a.approver_id = r.requester_id
        WHERE a.entity_id = ?
        """,
        (request_id,),
    ).fetchall()

    events = cur.execute(
        "SELECT * FROM audit_events WHERE entity_id = ? ORDER BY event_timestamp",
        (request_id,),
    ).fetchall()

    conn.close()
    return {
        "request": dict(pr),
        "lines": [dict(l) for l in lines],
        "approvals": [dict(a) for a in approvals],
        "audit_events": [dict(e) for e in events],
    }


@app.get("/api/rfqs")
def list_rfqs(limit: int = 50):
    conn = get_db()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT r.*, pr.total_estimated_amount, s.name as awarded_supplier_name
        FROM rfqs r
        JOIN purchase_requests pr ON r.request_id = pr.request_id
        LEFT JOIN suppliers s ON r.awarded_supplier_id = s.supplier_id
        ORDER BY r.issue_date DESC LIMIT ?
        """,
        (limit,),
    ).fetchall()
    results = [dict(row) for row in rows]
    conn.close()
    return results


@app.get("/api/rfqs/{rfq_id}/quotes")
def get_rfq_quotes(rfq_id: str):
    conn = get_db()
    cur = conn.cursor()
    quotes = cur.execute(
        """
        SELECT q.*, s.name as supplier_name, s.performance_rating, s.risk_level, s.on_time_delivery_rate
        FROM supplier_quotes q
        JOIN suppliers s ON q.supplier_id = s.supplier_id
        WHERE q.rfq_id = ?
        ORDER BY q.landed_cost_rank ASC
        """,
        (rfq_id,),
    ).fetchall()
    conn.close()
    return [dict(q) for q in quotes]


@app.get("/api/purchase-orders")
def list_purchase_orders(limit: int = 50):
    conn = get_db()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT po.*, s.name as supplier_name
        FROM purchase_orders po
        JOIN suppliers s ON po.supplier_id = s.supplier_id
        ORDER BY po.po_date DESC LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/api/deliveries")
def list_deliveries(limit: int = 50):
    conn = get_db()
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT d.*, r.name as received_by_name
        FROM deliveries d
        JOIN requesters r ON d.received_by_user_id = r.requester_id
        ORDER BY d.delivery_date DESC LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/api/anomalies")
def list_anomalies():
    conn = get_db()
    cur = conn.cursor()
    rows = cur.execute("SELECT * FROM ground_truth ORDER BY severity, anomaly_id").fetchall()
    conn.close()
    return [dict(row) for row in rows]


@app.get("/api/audit-trail/{entity_id}")
def get_audit_trail(entity_id: str):
    conn = get_db()
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT * FROM audit_events WHERE entity_id = ? ORDER BY event_timestamp",
        (entity_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


class SimulationRequest(BaseModel):
    item_name: str = "High-Performance AI Accelerator PCIe 80GB"
    quantity: int = 5
    estimated_unit_price: float = 9500.0
    department_name: str = "Data Science & AI Research"
    requester_name: str = "Dr. Elena Vance (Staff Specialist)"
    category: str = "HARDWARE"


@app.get("/api/analytics/metrics")
def get_metrics_endpoint():
    engine = ProcurementMetricsEngine(DB_PATH)
    return engine.compute_all_metrics()


@app.post("/api/workflow/simulate")
def simulate_workflow_endpoint(req: Optional[SimulationRequest] = None):
    if req is None:
        req = SimulationRequest()
    result = execute_simulated_workflow(
        item_name=req.item_name,
        quantity=req.quantity,
        estimated_unit_price=req.estimated_unit_price,
        department_name=req.department_name,
        requester_name=req.requester_name,
        category=req.category,
    )
    return result


@app.get("/", response_class=HTMLResponse)
def index_page():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Yottaflex AI — Enterprise Procurement & Supplier Delivery System</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    :root {
      --bg-dark: #0f172a;
      --card-bg: #1e293b;
      --border-color: #334155;
      --accent: #38bdf8;
      --accent-hover: #0284c7;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
    }
    body {
      background-color: var(--bg-dark);
      color: var(--text-main);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    .navbar {
      background-color: #0b1120 !important;
      border-bottom: 1px solid var(--border-color);
    }
    .nav-tabs .nav-link {
      color: var(--text-muted);
      border: none;
      font-weight: 500;
      padding: 0.8rem 1.2rem;
    }
    .nav-tabs .nav-link.active {
      color: var(--accent);
      background-color: transparent;
      border-bottom: 2px solid var(--accent);
    }
    .card {
      background-color: var(--card-bg);
      border: 1px solid var(--border-color);
      border-radius: 8px;
    }
    .kpi-card {
      padding: 1.25rem;
      border-radius: 8px;
      background: linear-gradient(145deg, #1e293b, #172235);
      border: 1px solid var(--border-color);
    }
    .kpi-val {
      font-size: 1.8rem;
      font-weight: 700;
      color: #38bdf8;
    }
    .kpi-lbl {
      font-size: 0.85rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .table-dark {
      --bs-table-bg: var(--card-bg);
      --bs-table-border-color: var(--border-color);
    }
    .badge-critical { background-color: #dc2626; color: white; }
    .badge-high { background-color: #ea580c; color: white; }
    .badge-medium { background-color: #d97706; color: white; }
    .badge-low { background-color: #2563eb; color: white; }
    .tab-content { padding-top: 1.5rem; }
  </style>
</head>
<body>
  <nav class="navbar navbar-dark px-4 py-3">
    <div class="container-fluid">
      <span class="navbar-brand mb-0 h1 fs-4">
        <i class="fa-solid fa-layer-group text-info me-2"></i><strong>Yottaflex AI</strong> Procurement & Supplier Delivery Engine
      </span>
      <span class="badge bg-success-subtle text-success border border-success px-3 py-2">
        <i class="fa-solid fa-circle-check me-1"></i> Governance & Verification Ready
      </span>
    </div>
  </nav>

  <div class="container-fluid px-4 py-4">
    <!-- KPI Row -->
    <div class="row g-3 mb-4" id="kpi-container">
      <div class="col-md-3">
        <div class="kpi-card">
          <div class="kpi-lbl">Purchase Requests</div>
          <div class="kpi-val" id="kpi-prs">—</div>
          <small class="text-muted">Multi-tier approvals applied</small>
        </div>
      </div>
      <div class="col-md-3">
        <div class="kpi-card">
          <div class="kpi-lbl">RFQs & Quotes</div>
          <div class="kpi-val" id="kpi-quotes">—</div>
          <small class="text-muted">Min 3 quotes evaluated per bid</small>
        </div>
      </div>
      <div class="col-md-3">
        <div class="kpi-card">
          <div class="kpi-lbl">Purchase Orders Issued</div>
          <div class="kpi-val" id="kpi-pos">—</div>
          <small class="text-muted" id="kpi-spend">Total spend: $0</small>
        </div>
      </div>
      <div class="col-md-3">
        <div class="kpi-card">
          <div class="kpi-lbl">Injected Anomalies (Ground Truth)</div>
          <div class="kpi-val text-warning" id="kpi-anomalies">—</div>
          <small class="text-muted">Isolated for audit benchmarking</small>
        </div>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <ul class="nav nav-tabs" id="mainTab" role="tablist">
      <li class="nav-item">
        <button class="nav-link active" data-bs-toggle="tab" data-bs-target="#prs-tab">
          <i class="fa-solid fa-file-invoice me-1"></i> Purchase Requests
        </button>
      </li>
      <li class="nav-item">
        <button class="nav-link" data-bs-toggle="tab" data-bs-target="#rfq-tab">
          <i class="fa-solid fa-scale-balanced me-1"></i> RFQs & Quote Matrix
        </button>
      </li>
      <li class="nav-item">
        <button class="nav-link" data-bs-toggle="tab" data-bs-target="#po-tab">
          <i class="fa-solid fa-truck me-1"></i> Purchase Orders & Delivery
        </button>
      </li>
      <li class="nav-item">
        <button class="nav-link" data-bs-toggle="tab" data-bs-target="#audit-tab">
          <i class="fa-solid fa-shield-halved me-1"></i> Audit Engine & Ground Truth
        </button>
      </li>
      <li class="nav-item">
        <button class="nav-link" data-bs-toggle="tab" data-bs-target="#trace-tab">
          <i class="fa-solid fa-timeline me-1"></i> Traceability Inspector
        </button>
      </li>
    </ul>

    <!-- Tab Contents -->
    <div class="tab-content">
      <!-- PRs Tab -->
      <div class="tab-pane fade show active" id="prs-tab">
        <div class="card p-3">
          <div class="d-flex justify-content-between align-items-center mb-3">
            <h5 class="mb-0">Purchase Requests & Approval Threshold Routing</h5>
            <span class="text-muted small">Showing latest 50 records</span>
          </div>
          <div class="table-responsive">
            <table class="table table-dark table-hover table-sm">
              <thead>
                <tr>
                  <th>Request ID</th>
                  <th>Requester</th>
                  <th>Department</th>
                  <th>Category</th>
                  <th>Amount (USD)</th>
                  <th>Tier Required</th>
                  <th>Method</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody id="table-prs-body"></tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- RFQ Tab -->
      <div class="tab-pane fade" id="rfq-tab">
        <div class="card p-3">
          <h5 class="mb-3">Competitive Sourcing & Landed Cost Quote Evaluation</h5>
          <div class="table-responsive">
            <table class="table table-dark table-hover table-sm">
              <thead>
                <tr>
                  <th>RFQ ID</th>
                  <th>PR ID</th>
                  <th>Issue Date</th>
                  <th>Deadline</th>
                  <th>Quotes Count</th>
                  <th>Awarded Supplier</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody id="table-rfqs-body"></tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- PO Tab -->
      <div class="tab-pane fade" id="po-tab">
        <div class="card p-3">
          <h5 class="mb-3">Purchase Orders & Inbound Deliveries</h5>
          <div class="table-responsive">
            <table class="table table-dark table-hover table-sm">
              <thead>
                <tr>
                  <th>PO ID</th>
                  <th>PR ID</th>
                  <th>Supplier</th>
                  <th>PO Date</th>
                  <th>Required Delivery</th>
                  <th>Total Amount</th>
                  <th>Approval Ref</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody id="table-pos-body"></tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Audit Tab -->
      <div class="tab-pane fade" id="audit-tab">
        <div class="card p-3 mb-4">
          <h5 class="mb-3">Labelled Edge Cases & Ground Truth Anomalies</h5>
          <p class="text-muted small">
            These labelled negative scenarios were injected systematically with deterministic rules. 
            They are isolated in <code>ground_truth.csv</code> to prevent feature leakage.
          </p>
          <div class="table-responsive">
            <table class="table table-dark table-hover table-sm">
              <thead>
                <tr>
                  <th>Anomaly ID</th>
                  <th>Entity Type</th>
                  <th>Entity ID</th>
                  <th>Issue Type</th>
                  <th>Severity</th>
                  <th>Rule Violated</th>
                  <th>Description</th>
                </tr>
              </thead>
              <tbody id="table-anomalies-body"></tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Trace Tab -->
      <div class="tab-pane fade" id="trace-tab">
        <div class="card p-3">
          <h5 class="mb-3">End-to-End Traceability & Audit Event Log</h5>
          <div class="input-group mb-3" style="max-width: 500px;">
            <input type="text" id="trace-input" class="form-control" placeholder="Enter PR, RFQ, PO, or Delivery ID (e.g. PR-2026-000001)">
            <button class="btn btn-info" onclick="fetchTrace()">Inspect History</button>
          </div>
          <div id="trace-results">
            <div class="text-muted">Enter an identifier above to inspect its full event timeline.</div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
  <script>
    async function loadStats() {
      try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        document.getElementById('kpi-prs').innerText = data.total_purchase_requests.toLocaleString();
        document.getElementById('kpi-quotes').innerText = data.total_rfqs.toLocaleString() + ' / ' + data.total_supplier_quotes.toLocaleString();
        document.getElementById('kpi-pos').innerText = data.total_purchase_orders.toLocaleString();
        document.getElementById('kpi-spend').innerText = 'Total PO Spend: $' + Number(data.total_committed_po_spend_usd).toLocaleString();
        document.getElementById('kpi-anomalies').innerText = data.total_ground_truth_anomalies.toLocaleString();
      } catch (err) {
        console.error(err);
      }
    }

    async function loadPRs() {
      try {
        const res = await fetch('/api/requests?limit=50');
        const prs = await res.json();
        const tbody = document.getElementById('table-prs-body');
        tbody.innerHTML = prs.map(p => `
          <tr>
            <td><code>${p.request_id}</code></td>
            <td>${p.requester_name}</td>
            <td>${p.department_name}</td>
            <td><span class="badge bg-secondary">${p.category}</span></td>
            <td>$${Number(p.total_estimated_amount).toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
            <td><span class="badge bg-info text-dark">${p.approval_tier_required}</span></td>
            <td>${p.procurement_method}</td>
            <td><span class="badge bg-success">${p.status}</span></td>
          </tr>
        `).join('');
      } catch (err) {
        console.error(err);
      }
    }

    async function loadRFQs() {
      try {
        const res = await fetch('/api/rfqs?limit=50');
        const rfqs = await res.json();
        const tbody = document.getElementById('table-rfqs-body');
        tbody.innerHTML = rfqs.map(r => `
          <tr>
            <td><code>${r.rfq_id}</code></td>
            <td><code>${r.request_id}</code></td>
            <td>${r.issue_date.split('T')[0]}</td>
            <td>${r.submission_deadline.split('T')[0]}</td>
            <td>${r.quotes_received_count} quotes</td>
            <td>${r.awarded_supplier_name || '<span class="text-muted">—</span>'}</td>
            <td><span class="badge bg-primary">${r.status}</span></td>
            <td><button class="btn btn-sm btn-outline-info" onclick="inspectQuotes('${r.rfq_id}')">View Quotes</button></td>
          </tr>
        `).join('');
      } catch (err) {
        console.error(err);
      }
    }

    async function inspectQuotes(rfqId) {
      const res = await fetch('/api/rfqs/' + rfqId + '/quotes');
      const quotes = await res.json();
      alert('Quotes for ' + rfqId + ':\\n' + quotes.map(q => 
        q.supplier_name + ' | Rank #' + q.landed_cost_rank + ' | Landed: $' + q.total_landed_cost_usd + ' | Status: ' + q.quote_status
      ).join('\\n'));
    }

    async function loadPOs() {
      try {
        const res = await fetch('/api/purchase-orders?limit=50');
        const pos = await res.json();
        const tbody = document.getElementById('table-pos-body');
        tbody.innerHTML = pos.map(p => `
          <tr>
            <td><code>${p.po_id}</code></td>
            <td><code>${p.request_id}</code></td>
            <td>${p.supplier_name}</td>
            <td>${p.po_date}</td>
            <td>${p.required_delivery_date}</td>
            <td>$${Number(p.total_po_amount).toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
            <td>${p.approval_reference_id ? '<code>' + p.approval_reference_id + '</code>' : '<span class="badge badge-critical">MISSING (ANOMALY)</span>'}</td>
            <td><span class="badge bg-success">${p.status}</span></td>
          </tr>
        `).join('');
      } catch (err) {
        console.error(err);
      }
    }

    async function loadAnomalies() {
      try {
        const res = await fetch('/api/anomalies');
        const anos = await res.json();
        const tbody = document.getElementById('table-anomalies-body');
        tbody.innerHTML = anos.map(a => `
          <tr>
            <td><code>${a.anomaly_id}</code></td>
            <td>${a.entity_type}</td>
            <td><code>${a.entity_id}</code></td>
            <td><strong>${a.issue_type}</strong></td>
            <td><span class="badge badge-${a.severity.toLowerCase()}">${a.severity}</span></td>
            <td>${a.rule_violated}</td>
            <td>${a.description}</td>
          </tr>
        `).join('');
      } catch (err) {
        console.error(err);
      }
    }

    async function fetchTrace() {
      const id = document.getElementById('trace-input').value.trim();
      if (!id) return;
      const res = await fetch('/api/audit-trail/' + id);
      const events = await res.json();
      const cont = document.getElementById('trace-results');
      if (events.length === 0) {
        cont.innerHTML = '<div class="alert alert-warning">No audit history found for ' + id + '</div>';
        return;
      }
      cont.innerHTML = `
        <h6 class="mt-3">Audit Trail for <code>${id}</code> (${events.length} state events recorded):</h6>
        <div class="list-group">
          ${events.map(e => `
            <div class="list-group-item list-group-item-dark border-secondary">
              <div class="d-flex w-100 justify-content-between">
                <h6 class="mb-1 text-info">${e.action_type}</h6>
                <small class="text-muted">${e.event_timestamp}</small>
              </div>
              <p class="mb-1">${e.details}</p>
              <small class="text-muted">Actor: <strong>${e.actor_id}</strong> | State: <em>${e.previous_state || 'N/A'} &rarr; ${e.new_state}</em></small>
            </div>
          `).join('')}
        </div>
      `;
    }

    // Initial load
    loadStats();
    loadPRs();
    loadRFQs();
    loadPOs();
    loadAnomalies();
  </script>
</body>
</html>
    """

