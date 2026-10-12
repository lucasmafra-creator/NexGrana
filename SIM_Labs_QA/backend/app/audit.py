from sqlalchemy.orm import Session
from .models import AuditEvent
from .auth import Principal


def record_event(db: Session, principal: Principal | None, action: str, object_type: str, object_id: str | None = None, product_id: str | None = None, reason: str | None = None) -> AuditEvent:
    event = AuditEvent(
        actor_member_id=principal.member_id if principal else None,
        actor_type="human" if principal else "service",
        action=action,
        object_type=object_type,
        object_id=object_id,
        product_id=product_id,
        reason=reason,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
