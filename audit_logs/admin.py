from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "actor",
        "action",
        "entity_type",
        "entity_id",
        "is_generated",
    )
    list_filter = ("action", "entity_type", "created_at", "is_generated")
    search_fields = ("description", "entity_type", "entity_id", "actor__username")
    readonly_fields = (
        "actor",
        "action",
        "entity_type",
        "entity_id",
        "description",
        "ip_address",
        "created_at",
        "is_generated",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
