"""Evaluate the Phase 0 gate from explicitly attested physical captures only.

Manifest: [{"path": "relative/capture.npz", "kind": "genuine" | "attack",
"object": "ceramic", "lighting": "indoor", "device": "laptop",
"attack": null | "print" | "screen" | "replay", "physical_recording": true}]
Paths are relative to the manifest. Requires the full 3x3x2 matrix, not just n=18.
Synthetic tests and generated signal fixtures cannot pass this physical gate.
"""

import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
from pol_verifier.engine import verify


def evaluate(manifest: Path) -> dict:
    entries = json.loads(manifest.read_text())
    seen, rows = set(), []
    for entry in entries:
        path = manifest.parent / entry["path"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if entry.get("physical_recording") is not True or digest in seen:
            raise ValueError("Each entry must attest a distinct physical recording")
        seen.add(digest)
        with np.load(path, allow_pickle=False) as data:
            metadata = json.loads(str(data["metadata_json"]))
            if "synthetic" in str(metadata).lower():
                raise ValueError("Synthetic data cannot be included in the physical gate")
            challenge = json.loads(str(data["challenge_json"]))
            report = verify(data["frames"], data["times_ms"], data["paint_ms"], challenge)
        rows.append(
            {
                **entry,
                "sha256": digest,
                "matches": report["matches"],
                "verdict": report["verdict"],
                "analysis_ms": report["elapsed_ms"],
            }
        )
    genuine = [r for r in rows if r["kind"] == "genuine"]
    attacks = [r for r in rows if r["kind"] == "attack"]
    objects = {r["object"] for r in genuine}
    lights = {r["lighting"] for r in genuine}
    devices = {r["device"] for r in genuine}
    combos = {(r["object"], r["lighting"], r["device"]) for r in genuine}
    complete = set(itertools.product(objects, lights, devices)) <= combos
    coverage = len(objects) >= 3 and len(lights) >= 3 and len(devices) >= 2 and complete
    attack_coverage = {r.get("attack") for r in attacks} >= {"print", "screen", "replay"}
    # Gross integrity failures never count as a genuine successful decode.
    pass_rate = sum(r["matches"] >= 8 and r["verdict"] != "FAILED" for r in genuine) / max(
        1, len(genuine)
    )
    passed = (
        coverage
        and attack_coverage
        and pass_rate >= 0.8
        and all(r["matches"] <= 4 for r in attacks)
    )
    return {
        "gate": "PASS" if passed else "NOT_PASSED",
        "genuine_n": len(genuine),
        "attack_n": len(attacks),
        "matrix_complete": coverage,
        "attack_coverage": attack_coverage,
        "genuine_decode_rate_at_8": pass_rate,
        "rows": rows,
        "note": "This physical gate alone cannot establish trusted camera capture or fraud resistance.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate(args.manifest)
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(text)
    print(text)
    raise SystemExit(0 if result["gate"] == "PASS" else 1)
