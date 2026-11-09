"""
Reproducibility Test Suite.
Verifies that two consecutive runs with seed 20261022 produce 100% bitwise identical files.
"""
import os
import shutil
import hashlib
from src.generator.synth_generator import SyntheticProcurementGenerator
from src.export.exporter import DataExporter


def hash_directory(directory: str):
    """Compute sha256 hash for every file in a directory."""
    hashes = {}
    for root, _, files in os.walk(directory):
        for f in sorted(files):
            if f == "manifest.json":  # Contains generation timestamp
                continue
            fpath = os.path.join(root, f)
            relpath = os.path.relpath(fpath, directory).replace("\\", "/")
            h = hashlib.sha256()
            with open(fpath, "rb") as bf:
                while chunk := bf.read(65536):
                    h.update(chunk)
            hashes[relpath] = h.hexdigest()
    return hashes


def test_reproducibility():
    seed = 20261022
    scale = "starter"

    run1_dir = "data/test_run1"
    run2_dir = "data/test_run2"

    if os.path.exists(run1_dir):
        shutil.rmtree(run1_dir)
    if os.path.exists(run2_dir):
        shutil.rmtree(run2_dir)

    # Run 1
    gen1 = SyntheticProcurementGenerator(seed=seed, scale=scale)
    b1 = gen1.generate_all()
    exp1 = DataExporter(b1, output_root=run1_dir)
    exp1.export_all(seed=seed, scale=scale)
    hashes1 = hash_directory(run1_dir)

    # Run 2
    gen2 = SyntheticProcurementGenerator(seed=seed, scale=scale)
    b2 = gen2.generate_all()
    exp2 = DataExporter(b2, output_root=run2_dir)
    exp2.export_all(seed=seed, scale=scale)
    hashes2 = hash_directory(run2_dir)

    # Compare
    assert len(hashes1) > 0, "No files generated in Run 1"
    assert hashes1.keys() == hashes2.keys(), "File sets do not match between runs"

    mismatches = []
    for f, h1 in hashes1.items():
        h2 = hashes2[f]
        if h1 != h2:
            mismatches.append((f, h1, h2))

    # Clean up test directories
    shutil.rmtree(run1_dir, ignore_errors=True)
    shutil.rmtree(run2_dir, ignore_errors=True)

    assert not mismatches, f"Mismatches found in files: {mismatches}"
    print(f"Reproducibility test PASSED for {len(hashes1)} files!")


if __name__ == "__main__":
    test_reproducibility()

