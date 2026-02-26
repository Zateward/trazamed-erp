import hashlib
import hmac
from datetime import datetime, timezone
from typing import Optional
from app.core.config import settings


def compute_record_signature(data: str, timestamp: Optional[datetime] = None) -> str:
    """
    Simulate Firma Electrónica Avanzada (FEA) per NOM-024-SSA3-2012.

    ⚠️  PRODUCTION WARNING: This implementation uses HMAC-SHA256 as a development
    placeholder and does NOT meet legal requirements for NOM-024-SSA3-2012 compliance.
    In production, this MUST be replaced with proper FIEL/SAT certificate-based
    digital signatures using pyOpenSSL and SAT-issued X.509 certificates.
    """
    ts = (timestamp or datetime.now(timezone.utc)).isoformat()
    payload = f"{data}|{ts}|{settings.SECRET_KEY}"
    return hmac.new(
        settings.SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()  # type: ignore[attr-defined]


def verify_record_signature(data: str, signature: str, timestamp: datetime) -> bool:
    expected = compute_record_signature(data, timestamp)
    return hmac.compare_digest(expected, signature)
