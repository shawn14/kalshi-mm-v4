"""RSA-PSS request signing for Kalshi API v2."""
from __future__ import annotations

import base64
import datetime as dt
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


def load_private_key(path: str | Path):
    data = Path(path).read_bytes()
    return serialization.load_pem_private_key(data, password=None)


def sign_request(api_key: str, private_key, method: str, path: str) -> dict[str, str]:
    """Return headers required for Kalshi RSA-PSS auth."""
    ts_ms = int(dt.datetime.now(dt.timezone.utc).timestamp() * 1000)
    msg = f"{ts_ms}{method}{path}"
    sig = private_key.sign(msg.encode(), padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()),
        salt_length=padding.PSS.DIGEST_LENGTH,
    ), hashes.SHA256())
    return {
        "KALSHI-ACCESS-KEY": api_key,
        "KALSHI-ACCESS-TIMESTAMP": str(ts_ms),
        "KALSHI-ACCESS-SIGNATURE": base64.b64encode(sig).decode(),
    }
