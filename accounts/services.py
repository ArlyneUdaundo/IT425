from django.contrib.auth.models import Group, Permission


REGISTRAR_GROUP_NAME = "Registrar Operations"
REGISTRAR_APP_LABELS = {
    "students",
    "departments",
    "academics",
    "faculty",
    "admissions",
    "enrollment",
    "grading",
    "attendance",
    "documents",
    "audit_logs",
}


def provision_registrar_access(user):
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    group, _ = Group.objects.get_or_create(name=REGISTRAR_GROUP_NAME)
    permissions = Permission.objects.filter(
        content_type__app_label__in=REGISTRAR_APP_LABELS
    )
    group.permissions.set(permissions)
    user.groups.add(group)
