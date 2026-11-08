"""Reproduce a spike report without a web server or model key."""

import argparse
import json
from pathlib import Path

import numpy as np

from .engine import verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument(
        "--challenge", type=Path, help="Optional externally retained challenge JSON"
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    # Official API: https://numpy.org/doc/stable/reference/generated/numpy.load.html
    with np.load(args.capture, allow_pickle=False) as data:
        challenge = json.loads(
            args.challenge.read_text() if args.challenge else str(data["challenge_json"])
        )
        report = verify(data["frames"], data["times_ms"], data["paint_ms"], challenge)
    output = json.dumps(report, indent=2, allow_nan=False)
    if args.output:
        args.output.write_text(output + "\n")
    summary = {k: v for k, v in report.items() if k not in ("heatmap", "trace")}
    print(json.dumps(summary, indent=2, allow_nan=False))
    print("Offline reanalysis only: the CLI cannot attest server issuance or single use.")


if __name__ == "__main__":
    main()
