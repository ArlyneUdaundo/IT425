from django.contrib import admin

from .models import StudentDocument


@admin.register(StudentDocument)
class StudentDocumentAdmin(admin.ModelAdmin):
    list_display = ("document_number", "student", "document_type", "status", "issued_at")
    list_filter = ("document_type", "status")
    search_fields = ("document_number", "student__student_id", "student__last_name")
