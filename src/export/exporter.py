"""
Data Exporter for CSV, JSON, SQLite, and SQL DDL/DML.
Generates an audit manifest with SHA256 checksums.
"""
import os
import csv
import json
import sqlite3
import hashlib
from datetime import datetime
from typing import Dict, Any, List
from src.generator.synth_generator import ProcurementDataBundle


class DataExporter:
    def __init__(self, bundle: ProcurementDataBundle, output_root: str = "data"):
        self.bundle = bundle
        self.output_root = output_root
        self.csv_dir = os.path.join(output_root, "csv")
        self.json_dir = os.path.join(output_root, "json")
        self.sql_dir = os.path.join(output_root, "sql")
        self.sqlite_db_path = os.path.join(output_root, "procurement.db")
        self.manifest_path = os.path.join(output_root, "manifest.json")

        os.makedirs(self.csv_dir, exist_ok=True)
        os.makedirs(self.json_dir, exist_ok=True)
        os.makedirs(self.sql_dir, exist_ok=True)

    def _get_entity_map(self) -> Dict[str, List[Any]]:
        return {
            "departments": self.bundle.departments,
            "budgets": self.bundle.budgets,
            "requesters": self.bundle.requesters,
            "suppliers": self.bundle.suppliers,
            "purchase_requests": self.bundle.purchase_requests,
            "request_lines": self.bundle.request_lines,
            "rfqs": self.bundle.rfqs,
            "supplier_quotes": self.bundle.supplier_quotes,
            "quote_lines": self.bundle.quote_lines,
            "approvals": self.bundle.approvals,
            "purchase_orders": self.bundle.purchase_orders,
            "po_lines": self.bundle.po_lines,
            "deliveries": self.bundle.deliveries,
            "audit_events": self.bundle.audit_events,
            "ground_truth": self.bundle.ground_truth,
        }

    def export_csv(self):
        """Export all entities to CSV files."""
        for name, records in self._get_entity_map().items():
            if not records:
                continue
            filepath = os.path.join(self.csv_dir, f"{name}.csv")
            dicts = [r.model_dump() for r in records]
            fieldnames = list(dicts[0].keys())

            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in dicts:
                    # Format enum objects to their values
                    cleaned_row = {
                        k: (v.value if hasattr(v, "value") else v)
                        for k, v in row.items()
                    }
                    writer.writerow(cleaned_row)

    def export_json(self):
        """Export all entities to JSON files."""
        for name, records in self._get_entity_map().items():
            filepath = os.path.join(self.json_dir, f"{name}.json")
            dicts = [r.model_dump() for r in records]
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(dicts, f, indent=2, default=str)

    def export_sqlite(self):
        """Create and populate SQLite relational database."""
        if os.path.exists(self.sqlite_db_path):
            os.remove(self.sqlite_db_path)

        conn = sqlite3.connect(self.sqlite_db_path)
        cur = conn.cursor()

        # Execute DDL schema
        schema_sql = self.generate_schema_sql()
        cur.executescript(schema_sql)

        # Populate tables
        for name, records in self._get_entity_map().items():
            if not records:
                continue
            dicts = [r.model_dump() for r in records]
            cols = list(dicts[0].keys())
            placeholders = ",".join(["?"] * len(cols))
            sql = f"INSERT INTO {name} ({','.join(cols)}) VALUES ({placeholders})"

            rows = []
            for d in dicts:
                rows.append([
                    (v.value if hasattr(v, "value") else (1 if v is True else 0 if v is False else v))
                    for v in d.values()
                ])
            cur.executemany(sql, rows)

        conn.commit()
        conn.close()

    def generate_schema_sql(self) -> str:
        """Generate standard SQL DDL schema script."""
        return """
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
"""

    def export_sql_scripts(self):
        """Export schema.sql and seed_data.sql."""
        schema_file = os.path.join(self.sql_dir, "schema.sql")
        with open(schema_file, "w", encoding="utf-8") as f:
            f.write(self.generate_schema_sql())

        seed_file = os.path.join(self.sql_dir, "seed_data.sql")
        with open(seed_file, "w", encoding="utf-8") as f:
            f.write("-- Synthetic Seed Data Insert Script\n\n")
            for name, records in self._get_entity_map().items():
                if not records:
                    continue
                dicts = [r.model_dump() for r in records]
                cols = list(dicts[0].keys())

                for d in dicts:
                    formatted_vals = []
                    for v in d.values():
                        val = v.value if hasattr(v, "value") else v
                        if val is None:
                            formatted_vals.append("NULL")
                        elif isinstance(val, (int, float)):
                            formatted_vals.append(str(val))
                        elif isinstance(val, bool):
                            formatted_vals.append("1" if val else "0")
                        else:
                            clean_str = str(val).replace("'", "''")
                            formatted_vals.append(f"'{clean_str}'")

                    f.write(
                        f"INSERT INTO {name} ({','.join(cols)}) VALUES ({','.join(formatted_vals)});\n"
                    )

    def generate_manifest(self, seed: int, scale: str) -> Dict[str, Any]:
        """Generate manifest with file checksums, record counts, and provenance metadata."""
        manifest = {
            "dataset_name": "Yottaflex Procurement & Supplier Delivery Synthetic Dataset",
            "generation_timestamp": datetime.now().isoformat(),
            "generator_version": "1.0.0",
            "random_seed": seed,
            "scale_profile": scale,
            "provenance": {
                "lawful_use_type": "100% Synthetic Domain-Generated Data",
                "personal_data_included": False,
                "external_confidential_data": False,
                "license": "MIT / Creative Commons Zero (CC0)",
            },
            "table_summary": {},
            "file_checksums_sha256": {},
        }

        entity_map = self._get_entity_map()
        for name, records in entity_map.items():
            manifest["table_summary"][name] = {
                "record_count": len(records),
            }

        # Calculate file hashes
        for root, _, files in os.walk(self.output_root):
            for file in files:
                if file == "manifest.json":
                    continue
                fpath = os.path.join(root, file)
                relpath = os.path.relpath(fpath, self.output_root)
                hasher = hashlib.sha256()
                with open(fpath, "rb") as bf:
                    while chunk := bf.read(65536):
                        hasher.update(chunk)
                manifest["file_checksums_sha256"][relpath.replace("\\", "/")] = hasher.hexdigest()

        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        return manifest

    def export_all(self, seed: int, scale: str) -> Dict[str, Any]:
        """Execute full export suite across CSV, JSON, SQLite, SQL, and manifest."""
        self.export_csv()
        self.export_json()
        self.export_sqlite()
        self.export_sql_scripts()
        return self.generate_manifest(seed, scale)
