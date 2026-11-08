import json

from scripts.check_physics_gate import evaluate


def test_missing_physical_recordings_cannot_pass_gate(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text("[]")
    result = evaluate(manifest)
    assert result["gate"] == "NOT_PASSED"
    assert result["genuine_n"] == 0
    assert result["attack_n"] == 0
    assert result["matrix_complete"] is False


def test_numerical_fixture_cannot_be_attested_as_physical(tmp_path):
    import numpy as np
    import pytest

    path = tmp_path / "fake.npz"
    np.savez_compressed(path, metadata_json=json.dumps({"source": "SYNTHETIC_TEST"}))
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps([{"path": path.name, "physical_recording": True}]))
    with pytest.raises(ValueError, match="Synthetic"):
        evaluate(manifest)
