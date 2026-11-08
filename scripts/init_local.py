"""Prepare ignored local settings without exposing a merchant credential."""

import os
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / ".env"
template = (root / ".env.example").read_text()
template = template.replace(
    "POL_MERCHANT_TOKEN=\n", f"POL_MERCHANT_TOKEN={secrets.token_urlsafe(40)}\n"
)
try:
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
except FileExistsError:
    print("Existing .env kept unchanged. No credentials were overwritten.")
else:
    with os.fdopen(descriptor, "w") as file:
        file.write(template)
    print("Created ignored .env with a merchant credential. Add external sandbox keys locally.")
