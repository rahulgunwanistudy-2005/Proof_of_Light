"""Convert the browser's recovery JSON into a local NPZ after an upload failure."""

import argparse
import json
from pathlib import Path

from apps.api.main import Capture, decode_and_verify

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("input", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
data, report = decode_and_verify(Capture.model_validate(json.loads(args.input.read_text())))
args.output.write_bytes(data)
print(f"Saved {args.output}. Offline result: {report['verdict']}; {report['matches']}/10")
print("Offline recovery does not attest server challenge issuance or single use.")
