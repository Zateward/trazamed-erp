"""Audit trail service - NOM-024 compliant."""
import json
from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import AuditLog
from app.core.fea import compute_record_signature


async def log_action(
    db: AsyncSession,
    user_id: int,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    old_values: Optional[dict] = None,
    new_values: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> AuditLog:
    ts = datetime.now(timezone.utc)
    payload = json.dumps({
        "user_id": user_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "new_values": new_values,
    }, sort_keys=True)
    signature = compute_record_signature(payload, ts)

    log_entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        old_values=old_values,
        new_values=new_values,
        ip_address=ip_address,
        user_agent=user_agent,
        signature=signature,
        created_at=ts,
    )
    db.add(log_entry)
    await db.flush()
    return log_entry
