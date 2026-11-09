"""
Master Test Runner.
Executes validation tests, audit accuracy benchmarks, and reproducibility tests.
"""
import sys
from tests.test_validation import test_dataset_validation
from tests.test_audit_engine import test_audit_detection_accuracy
from tests.test_reproducibility import test_reproducibility


def main():
    print("=" * 60)
    print("RUNNING YOTTAFLEX PROCUREMENT SYSTEM VERIFICATION SUITE")
    print("=" * 60)

    print("\n[1/3] Running Relational & Arithmetic Validation Suite...")
    test_dataset_validation()

    print("\n[2/3] Running Audit Engine vs Ground Truth Accuracy Benchmark...")
    test_audit_detection_accuracy()

    print("\n[3/3] Running Bitwise Deterministic Reproducibility Test...")
    test_reproducibility()

    print("\n" + "=" * 60)
    print("[SUCCESS] ALL VERIFICATION SUITES COMPLETED AND PASSED 100%!")
    print("=" * 60)


if __name__ == "__main__":
    main()

