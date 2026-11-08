# Evaluation status

No physical performance, false-accept rate, false-reject rate or ROC/AUC claim is
available. The tests in `tests/` use generated numerical signals or HTTP test
fixtures. Browser automation uses Chromium's fake camera. None count toward the
physical gate or the later 40-genuine/40-attack held-out evaluation.

## Reproduce local checks
```sh
.venv/bin/python -m pytest -q
.venv/bin/ruff check apps/api packages scripts tests
node --check apps/spike/capture.js
```

With the local server running:
```sh
.venv/bin/python scripts/probe_injection.py
PLAYWRIGHT_BROWSERS_PATH=/tmp/pol-playwright .venv/bin/python scripts/browser_smoke.py --pass-name local
```

Download a real capture from the workbench, then reanalyze offline:
```sh
.venv/bin/pol-verify /absolute/path/to/capture.npz --output /tmp/report.json
```
The CLI loads arrays with `allow_pickle=False`; an NPZ is numeric arrays plus
Unicode JSON. Offline analysis cannot validate the original challenge HMAC or
single use without server records. Files are small-grid experimental data, not
original sensor frames or full-resolution damage evidence.

## Gate report
Follow `scripts/record_fixture.md`, then run:
```sh
.venv/bin/python scripts/check_physics_gate.py eval/fixtures/manifest.json --output eval/reports/physical-gate.json
```
Nonzero exit means the gate has not passed. It requires explicit physical-recording
attestation and the complete object x light x device matrix, plus all three attack
types. It rejects duplicate files and any metadata labeled synthetic.

## Confirmed counterexample
`2026-11-08-injection.json` records an actual request through the local HTTP
endpoint: synthetic uploaded frames were classified `VERIFIED`, 10/10. The
correlation and latency there are single-run measurements on this laptop, not
benchmark statistics. This is an algorithmic security failure even though the
positive numerical signal tests pass.

Do not count the script's generated frames as a genuine physical recording.
The guessing-null chance of 4^-10 does not apply to an attacker who reads the
challenge and constructs the pixels adaptively.
