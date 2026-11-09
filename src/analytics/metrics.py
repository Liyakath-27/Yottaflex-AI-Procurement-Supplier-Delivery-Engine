"""
Procurement Analytics and Operational Metrics Engine.
Computes measurable outputs across sourcing velocity, landed cost savings,
supplier performance scorecards, budget utilization, and governance compliance.
"""
import sqlite3
import os
from typing import Dict, Any, List


class ProcurementMetricsEngine:
    def __init__(self, db_path: str = "data/procurement.db"):
        self.db_path = db_path

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def compute_all_metrics(self) -> Dict[str, Any]:
        """Compute comprehensive metrics across all procurement domains."""
        conn = self._get_conn()
        cur = conn.cursor()

        # 1. Financial & Volume Overview
        overview = cur.execute("""
            SELECT 
                COUNT(DISTINCT pr.request_id) as total_requests,
                COUNT(DISTINCT po.po_id) as total_orders,
                COALESCE(SUM(pr.total_estimated_amount), 0) as total_pr_estimated_usd,
                COALESCE(SUM(po.total_po_amount), 0) as total_po_committed_usd,
                COALESCE(AVG(po.total_po_amount), 0) as avg_po_value_usd
            FROM purchase_requests pr
            LEFT JOIN purchase_orders po ON pr.request_id = po.request_id
        """).fetchone()

        # 2. Competitive Sourcing & Landed Cost Savings
        savings = cur.execute("""
            WITH QuoteStats AS (
                SELECT 
                    rfq_id,
                    MIN(total_landed_cost_usd) as min_cost,
                    MAX(total_landed_cost_usd) as max_cost,
                    AVG(total_landed_cost_usd) as avg_cost
                FROM supplier_quotes
                GROUP BY rfq_id
            ),
            AwardedQuotes AS (
                SELECT 
                    r.rfq_id,
                    q.total_landed_cost_usd as awarded_cost,
                    qs.min_cost,
                    qs.max_cost,
                    qs.avg_cost
                FROM rfqs r
                JOIN supplier_quotes q ON r.awarded_quote_id = q.quote_id
                JOIN QuoteStats qs ON r.rfq_id = qs.rfq_id
                WHERE r.status = 'AWARDED'
            )
            SELECT 
                COUNT(*) as competitive_rfqs_awarded,
                COALESCE(SUM(max_cost - awarded_cost), 0) as total_savings_vs_highest_bid_usd,
                COALESCE(SUM(avg_cost - awarded_cost), 0) as total_savings_vs_average_bid_usd,
                COALESCE(AVG((max_cost - awarded_cost) / NULLIF(max_cost, 0)), 0) * 100 as avg_pct_savings_vs_max
            FROM AwardedQuotes
        """).fetchone()

        # 3. Sourcing Lead Time & Delivery Velocity
        velocity = cur.execute("""
            SELECT 
                COALESCE(AVG(julianday(r.award_date) - julianday(r.issue_date)), 0) as avg_sourcing_cycle_days,
                COALESCE(AVG(julianday(d.delivery_date) - julianday(po.po_date)), 0) as avg_order_to_delivery_days,
                COALESCE(AVG(julianday(po.required_delivery_date) - julianday(d.delivery_date)), 0) as avg_days_ahead_of_deadline
            FROM purchase_orders po
            JOIN deliveries d ON po.po_id = d.po_id
            LEFT JOIN rfqs r ON po.rfq_id = r.rfq_id
        """).fetchone()

        # 4. Inbound Delivery Performance & Quality Inspection
        delivery_perf = cur.execute("""
            SELECT 
                COUNT(*) as total_shipments,
                SUM(CASE WHEN delivery_status = 'DELIVERED_ON_TIME' THEN 1 ELSE 0 END) as on_time_shipments,
                SUM(CASE WHEN delivery_status = 'DELIVERED_LATE' THEN 1 ELSE 0 END) as late_shipments,
                SUM(CASE WHEN is_partial = 1 THEN 1 ELSE 0 END) as partial_shipments,
                SUM(CASE WHEN inspection_status = 'PASSED' THEN 1 ELSE 0 END) as passed_inspection,
                SUM(CASE WHEN inspection_status = 'ACCEPTED_WITH_CONCESSION' THEN 1 ELSE 0 END) as concession_inspection
            FROM deliveries
        """).fetchone()

        # 5. Departmental Budget Utilization & Commitments
        budgets_data = cur.execute("""
            SELECT 
                d.department_name,
                COUNT(b.budget_id) as budget_count,
                SUM(b.allocated_amount) as total_allocated,
                SUM(b.committed_amount) as total_committed,
                SUM(b.spent_amount) as total_spent,
                SUM(b.remaining_balance) as total_remaining,
                ROUND((SUM(b.committed_amount + b.spent_amount) / SUM(b.allocated_amount)) * 100, 2) as utilization_pct
            FROM budgets b
            JOIN departments d ON b.department_id = d.department_id
            GROUP BY d.department_name
            ORDER BY utilization_pct DESC
        """).fetchall()

        # 6. Supplier Performance Distribution & Risk Tiering
        supplier_risk = cur.execute("""
            SELECT 
                risk_level,
                COUNT(*) as supplier_count,
                ROUND(AVG(performance_rating), 2) as avg_rating,
                ROUND(AVG(on_time_delivery_rate) * 100, 1) as avg_ontime_pct,
                ROUND(AVG(quality_score) * 100, 1) as avg_quality_pct
            FROM suppliers
            GROUP BY risk_level
            ORDER BY supplier_count DESC
        """).fetchall()

        # 7. Governance, Anomalies, and Audit Metrics
        anomalies_summary = cur.execute("""
            SELECT 
                severity,
                COUNT(*) as anomaly_count
            FROM ground_truth
            GROUP BY severity
            ORDER BY 
                CASE severity 
                    WHEN 'CRITICAL' THEN 1 
                    WHEN 'HIGH' THEN 2 
                    WHEN 'MEDIUM' THEN 3 
                    WHEN 'LOW' THEN 4 
                END
        """).fetchall()

        conn.close()

        total_ship = delivery_perf["total_shipments"] or 1
        return {
            "financial_overview": {
                "total_purchase_requests": overview["total_requests"],
                "total_purchase_orders": overview["total_orders"],
                "total_pr_estimated_usd": round(overview["total_pr_estimated_usd"], 2),
                "total_po_committed_usd": round(overview["total_po_committed_usd"], 2),
                "average_po_value_usd": round(overview["avg_po_value_usd"], 2),
            },
            "sourcing_cost_savings": {
                "competitive_rfqs_awarded": savings["competitive_rfqs_awarded"],
                "total_savings_vs_highest_bid_usd": round(savings["total_savings_vs_highest_bid_usd"], 2),
                "total_savings_vs_average_bid_usd": round(savings["total_savings_vs_average_bid_usd"], 2),
                "average_savings_percentage": round(savings["avg_pct_savings_vs_max"], 2),
            },
            "operational_velocity": {
                "average_sourcing_cycle_days": round(velocity["avg_sourcing_cycle_days"], 1),
                "average_order_to_delivery_days": round(velocity["avg_order_to_delivery_days"], 1),
                "average_days_ahead_of_deadline": round(velocity["avg_days_ahead_of_deadline"], 1),
            },
            "delivery_and_quality": {
                "total_shipments_recorded": total_ship,
                "on_time_rate_pct": round((delivery_perf["on_time_shipments"] / total_ship) * 100, 1),
                "late_shipment_rate_pct": round((delivery_perf["late_shipments"] / total_ship) * 100, 1),
                "partial_shipment_count": delivery_perf["partial_shipments"],
                "quality_inspection_pass_rate_pct": round((delivery_perf["passed_inspection"] / total_ship) * 100, 1),
                "concession_acceptance_count": delivery_perf["concession_inspection"],
            },
            "departmental_budget_utilization": [
                {
                    "department_name": row["department_name"],
                    "budget_count": row["budget_count"],
                    "total_allocated_usd": round(row["total_allocated"], 2),
                    "total_committed_usd": round(row["total_committed"], 2),
                    "total_spent_usd": round(row["total_spent"], 2),
                    "total_remaining_usd": round(row["total_remaining"], 2),
                    "utilization_pct": row["utilization_pct"],
                }
                for row in budgets_data
            ],
            "supplier_risk_scorecard": [
                {
                    "risk_level": row["risk_level"],
                    "supplier_count": row["supplier_count"],
                    "average_rating": row["avg_rating"],
                    "average_ontime_rate_pct": row["avg_ontime_pct"],
                    "average_quality_score_pct": row["avg_quality_pct"],
                }
                for row in supplier_risk
            ],
            "governance_anomalies_by_severity": [
                {
                    "severity": row["severity"],
                    "count": row["anomaly_count"],
                }
                for row in anomalies_summary
            ],
        }

