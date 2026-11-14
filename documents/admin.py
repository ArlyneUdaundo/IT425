from django.contrib import admin

from .models import StudentDocument


@admin.register(StudentDocument)
class StudentDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "document_number",
        "student",
        "document_type",
        "status",
        "issued_at",
        "is_generated",
    )
    list_filter = ("document_type", "status", "is_generated")
    search_fields = ("document_number", "student__student_id", "student__last_name")
    readonly_fields = ("is_generated",)
