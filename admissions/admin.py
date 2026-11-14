from django.contrib import admin

from .models import AdmissionApplication, AdmissionDocument


class AdmissionDocumentInline(admin.TabularInline):
    model = AdmissionDocument
    extra = 0
    readonly_fields = ("is_generated",)


@admin.register(AdmissionApplication)
class AdmissionApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "application_number",
        "last_name",
        "first_name",
        "preferred_course",
        "status",
        "submitted_at",
        "is_generated",
    )
    list_filter = ("status", "preferred_course")
    search_fields = ("application_number", "first_name", "last_name", "email")
    readonly_fields = ("submitted_at", "reviewed_at", "is_generated")
    inlines = [AdmissionDocumentInline]


@admin.register(AdmissionDocument)
class AdmissionDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "application",
        "requirement_name",
        "status",
        "reviewed_at",
        "is_generated",
    )
    list_filter = ("status",)
    readonly_fields = ("is_generated",)
