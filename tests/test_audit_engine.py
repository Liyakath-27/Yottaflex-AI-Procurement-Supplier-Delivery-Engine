"""
Audit Engine Test Suite.
Verifies that rule-based compliance auditing accurately detects injected anomalies.
"""
from src.generator.synth_generator import SyntheticProcurementGenerator
from src.engine.audit_engine import ProcurementAuditor


def test_audit_detection_accuracy():
    seed = 20261022
    scale = "starter"

    gen = SyntheticProcurementGenerator(seed=seed, scale=scale)
    bundle = gen.generate_all()

    auditor = ProcurementAuditor(
        departments=bundle.departments,
        budgets=bundle.budgets,
        requesters=bundle.requesters,
        suppliers=bundle.suppliers,
        requests=bundle.purchase_requests,
        request_lines=bundle.request_lines,
        rfqs=bundle.rfqs,
        quotes=bundle.supplier_quotes,
        approvals=bundle.approvals,
        pos=bundle.purchase_orders,
        po_lines=bundle.po_lines,
        deliveries=bundle.deliveries,
    )

    findings = auditor.scan_all()
    eval_metrics = auditor.evaluate_against_ground_truth(bundle.ground_truth)

    print("Audit Accuracy Metrics:")
    print(f"  Total Ground Truth : {eval_metrics['total_ground_truth']}")
    print(f"  Total Detected     : {eval_metrics['total_detected']}")
    print(f"  True Positives     : {eval_metrics['true_positives']}")
    print(f"  Precision          : {eval_metrics['overall_precision'] * 100:.2f}%")
    print(f"  Recall             : {eval_metrics['overall_recall'] * 100:.2f}%")
    print(f"  F1-Score           : {eval_metrics['overall_f1_score'] * 100:.2f}%")
    import json
    print("Breakdown:", json.dumps(eval_metrics["breakdown_by_type"], indent=2))

    assert eval_metrics["overall_precision"] >= 0.90, f"Precision below 90%: {eval_metrics['overall_precision']}"
    assert eval_metrics["overall_recall"] >= 0.90, f"Recall below 90%: {eval_metrics['overall_recall']}"
    print("Audit engine test PASSED!")


if __name__ == "__main__":
    test_audit_detection_accuracy()
