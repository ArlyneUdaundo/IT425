from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from .models import AuditLog


@receiver(user_logged_in)
def record_login(sender, request, user, **kwargs):
    AuditLog.objects.create(
        actor=user,
        action=AuditLog.Action.LOGIN,
        entity_type="accounts.User",
        entity_id=str(user.pk),
        description=f"{user.get_username()} signed in.",
        ip_address=request.META.get("REMOTE_ADDR"),
    )


@receiver(user_logged_out)
def record_logout(sender, request, user, **kwargs):
    AuditLog.objects.create(
        actor=user if user and user.is_authenticated else None,
        action=AuditLog.Action.LOGOUT,
        entity_type="accounts.User",
        entity_id=str(user.pk) if user else "",
        description=f"{user.get_username()} signed out."
        if user
        else "An anonymous session ended.",
        ip_address=request.META.get("REMOTE_ADDR") if request else None,
    )
