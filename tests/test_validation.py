"""
Validation Test Suite.
Verifies relational integrity, foreign keys, primary keys, and arithmetic reconciliations.
"""
from src.generator.synth_generator import SyntheticProcurementGenerator
from src.validation.validator import DatasetValidator


def test_dataset_validation():
    seed = 20261022
    scale = "starter"

    gen = SyntheticProcurementGenerator(seed=seed, scale=scale)
    bundle = gen.generate_all()

    validator = DatasetValidator(bundle)
    res = validator.run_all_validations()

    print(f"Validation executed {res.total_checks} checks.")
    print(f"Passed: {res.passed_checks}, Failed: {res.failed_checks}")

    if res.errors:
        for e in res.errors:
            print("ERROR:", e)

    assert res.is_valid is True, f"Validation failed with {res.failed_checks} errors: {res.errors}"
    assert res.failed_checks == 0, f"Expected 0 failed checks, got {res.failed_checks}"
    print("Dataset validation test PASSED!")


if __name__ == "__main__":
    test_dataset_validation()

