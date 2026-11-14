from .models import AuditLog


def record_activity(*, actor, action, entity, description, request=None):
    ip_address = None
    if request:
        ip_address = request.META.get("REMOTE_ADDR")
    return AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        action=action,
        entity_type=entity._meta.label,
        entity_id=str(entity.pk),
        description=description,
        ip_address=ip_address,
    )
