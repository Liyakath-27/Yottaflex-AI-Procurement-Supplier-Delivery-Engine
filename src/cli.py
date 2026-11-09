"""
Unified Command-Line Interface (CLI) for the Procurement & Supplier Delivery System.
"""
import os
import sys
import json
import hashlib
import click

from src.generator.synth_generator import SyntheticProcurementGenerator
from src.export.exporter import DataExporter
from src.validation.validator import DatasetValidator
from src.engine.audit_engine import ProcurementAuditor
from src.analytics.metrics import ProcurementMetricsEngine


@click.group()
def cli():
    """Yottaflex Procurement & Supplier Delivery System CLI."""
    pass


@cli.command()
@click.option("--seed", default=20261022, help="Fixed random seed for deterministic generation.")
@click.option("--scale", type=click.Choice(["starter", "full"]), default="full", help="Dataset scale.")
@click.option("--outdir", default="data", help="Output directory path.")
def generate(seed: int, scale: str, outdir: str):
    """Generate synthetic procurement data across all entities."""
    click.echo(f"[*] Initializing Synthetic Generator (Seed={seed}, Scale={scale})...")
    gen = SyntheticProcurementGenerator(seed=seed, scale=scale)
    bundle = gen.generate_all()

    click.echo("[*] Exporting datasets to CSV, JSON, SQLite, and SQL scripts...")
    exporter = DataExporter(bundle, output_root=outdir)
    manifest = exporter.export_all(seed=seed, scale=scale)

    click.echo("[+] Generation and export completed successfully!")
    click.echo("\nTable Record Summary:")
    for tbl, info in manifest["table_summary"].items():
        click.echo(f"  - {tbl:<22}: {info['record_count']:>6} records")
    click.echo(f"\nManifest saved to: {os.path.join(outdir, 'manifest.json')}")


@cli.command()
@click.option("--seed", default=20261022, help="Fixed random seed.")
@click.option("--scale", type=click.Choice(["starter", "full"]), default="full", help="Scale profile.")
def validate(seed: int, scale: str):
    """Run comprehensive validation tests on generated data."""
    click.echo(f"[*] Generating in-memory dataset for validation (Seed={seed}, Scale={scale})...")
    gen = SyntheticProcurementGenerator(seed=seed, scale=scale)
    bundle = gen.generate_all()

    click.echo("[*] Executing validation suite...")
    validator = DatasetValidator(bundle)
    res = validator.run_all_validations()

    click.echo("\n" + "=" * 50)
    click.echo(f"Validation Status : {'PASSED' if res.is_valid else 'FAILED'}")
    click.echo(f"Total Checks      : {res.total_checks}")
    click.echo(f"Passed Checks     : {res.passed_checks}")
    click.echo(f"Failed Checks     : {res.failed_checks}")
    click.echo(f"Warnings          : {len(res.warnings)}")
    click.echo("=" * 50)

    if res.errors:
        click.echo("\nErrors:")
        for err in res.errors:
            click.echo(f"  [X] {err}")

    if res.warnings:
        click.echo("\nWarnings:")
        for warn in res.warnings:
            click.echo(f"  [!] {warn}")

    if "audit_engine_evaluation" in res.metrics:
        m = res.metrics["audit_engine_evaluation"]
        click.echo("\nAudit Engine vs Ground Truth Accuracy:")
        click.echo(f"  Ground Truth Anomalies : {m['total_ground_truth']}")
        click.echo(f"  Detected Anomalies     : {m['total_detected']}")
        click.echo(f"  True Positives         : {m['true_positives']}")
        click.echo(f"  False Positives        : {m['false_positives']}")
        click.echo(f"  False Negatives        : {m['false_negatives']}")
        click.echo(f"  Overall Precision      : {m['overall_precision'] * 100:.2f}%")
        click.echo(f"  Overall Recall         : {m['overall_recall'] * 100:.2f}%")
        click.echo(f"  Overall F1-Score       : {m['overall_f1_score'] * 100:.2f}%")


@cli.command()
@click.option("--seed", default=20261022, help="Seed to test reproducibility.")
@click.option("--scale", type=click.Choice(["starter", "full"]), default="starter", help="Scale profile.")
def reproduce(seed: int, scale: str):
    """Test bitwise reproducibility across two consecutive generation runs."""
    click.echo(f"[*] Running Run 1 with seed {seed}...")
    gen1 = SyntheticProcurementGenerator(seed=seed, scale=scale)
    b1 = gen1.generate_all()
    exp1 = DataExporter(b1, output_root="data/run1")
    m1 = exp1.export_all(seed=seed, scale=scale)

    click.echo(f"[*] Running Run 2 with seed {seed}...")
    gen2 = SyntheticProcurementGenerator(seed=seed, scale=scale)
    b2 = gen2.generate_all()
    exp2 = DataExporter(b2, output_root="data/run2")
    m2 = exp2.export_all(seed=seed, scale=scale)

    click.echo("\nComparing SHA256 checksums across runs:")
    all_match = True
    files1 = m1["file_checksums_sha256"]
    files2 = m2["file_checksums_sha256"]

    for fpath, hash1 in files1.items():
        hash2 = files2.get(fpath)
        match = (hash1 == hash2)
        status = "MATCH" if match else "MISMATCH"
        if not match:
            all_match = False
        click.echo(f"  [{status}] {fpath}")

    click.echo("=" * 50)
    if all_match:
        click.echo("[+] REPRODUCIBILITY TEST PASSED: 100% bitwise identical output!")
    else:
        click.echo("[-] REPRODUCIBILITY TEST FAILED: Differences detected between runs.")

    # Clean up temporary run directories
    import shutil
    shutil.rmtree("data/run1", ignore_errors=True)
    shutil.rmtree("data/run2", ignore_errors=True)


@cli.command()
@click.option("--dbpath", default="data/procurement.db", help="Path to SQLite database.")
def metrics(dbpath: str):
    """Compute and display measurable procurement metrics and KPIs."""
    if not os.path.exists(dbpath):
        click.echo(f"[!] Database not found at {dbpath}. Please run `python -m src.cli generate` first.")
        return

    click.echo("[*] Computing Enterprise Procurement Metrics...\n")
    engine = ProcurementMetricsEngine(dbpath)
    res = engine.compute_all_metrics()

    fo = res["financial_overview"]
    click.echo("================ FINANCIAL & VOLUME OVERVIEW ================")
    click.echo(f"  Total Purchase Requests : {fo['total_purchase_requests']:,}")
    click.echo(f"  Total Purchase Orders   : {fo['total_purchase_orders']:,}")
    click.echo(f"  Total PR Estimated Value: ${fo['total_pr_estimated_usd']:,.2f}")
    click.echo(f"  Total PO Committed Spend: ${fo['total_po_committed_usd']:,.2f}")
    click.echo(f"  Average PO Value        : ${fo['average_po_value_usd']:,.2f}")

    sc = res["sourcing_cost_savings"]
    click.echo("\n================ COMPETITIVE SOURCING SAVINGS ===============")
    click.echo(f"  Competitive RFQs Awarded : {sc['competitive_rfqs_awarded']}")
    click.echo(f"  Savings vs Highest Bid   : ${sc['total_savings_vs_highest_bid_usd']:,.2f}")
    click.echo(f"  Savings vs Average Bid   : ${sc['total_savings_vs_average_bid_usd']:,.2f}")
    click.echo(f"  Average Savings Ratio    : {sc['average_savings_percentage']:.2f}%")

    vel = res["operational_velocity"]
    click.echo("\n================ OPERATIONAL SOURCING VELOCITY ==============")
    click.echo(f"  Avg RFQ Sourcing Cycle   : {vel['average_sourcing_cycle_days']} days")
    click.echo(f"  Avg Order-to-Delivery    : {vel['average_order_to_delivery_days']} days")
    click.echo(f"  Avg Ahead of Deadline    : {vel['average_days_ahead_of_deadline']} days")

    dq = res["delivery_and_quality"]
    click.echo("\n================ DELIVERY & QUALITY INSPECTION ==============")
    click.echo(f"  Total Inbound Shipments  : {dq['total_shipments_recorded']:,}")
    click.echo(f"  On-Time Delivery Rate    : {dq['on_time_rate_pct']}%")
    click.echo(f"  Late Delivery Rate       : {dq['late_shipment_rate_pct']}%")
    click.echo(f"  Partial Shipments        : {dq['partial_shipment_count']}")
    click.echo(f"  Quality Inspection Pass  : {dq['quality_inspection_pass_rate_pct']}%")
    click.echo(f"  Concession Acceptances   : {dq['concession_acceptance_count']}")

    click.echo("\n================ DEPARTMENTAL BUDGET UTILIZATION ============")
    for dept in res["departmental_budget_utilization"]:
        click.echo(
            f"  {dept['department_name']:<33} | "
            f"Alloc: ${dept['total_allocated_usd']:>12,.2f} | "
            f"Utilized: {dept['utilization_pct']:>5.1f}% | "
            f"Remaining: ${dept['total_remaining_usd']:>12,.2f}"
        )

    click.echo("\n================ SUPPLIER RISK SCORECARD ====================")
    for supp in res["supplier_risk_scorecard"]:
        click.echo(
            f"  Risk Tier: {supp['risk_level']:<8} | "
            f"Suppliers: {supp['supplier_count']:>3} | "
            f"Avg Rating: {supp['average_rating']}/5.0 | "
            f"On-Time: {supp['average_ontime_rate_pct']}% | "
            f"Quality: {supp['average_quality_score_pct']}%"
        )

    click.echo("\n================ GOVERNANCE ANOMALIES (GROUND TRUTH) ========")
    for ano in res["governance_anomalies_by_severity"]:
        click.echo(f"  Severity {ano['severity']:<8} : {ano['count']:>3} anomalies")
    click.echo("=============================================================")


@cli.command()
@click.option("--host", default="127.0.0.1", help="Host interface.")
@click.option("--port", default=8000, help="Listening port.")
def serve(host: str, port: int):
    """Start the interactive FastAPI web dashboard."""
    import uvicorn
    click.echo(f"[*] Starting Procurement Dashboard at http://{host}:{port}")
    uvicorn.run("src.api.app:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    cli()

