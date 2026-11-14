from django.contrib import admin

from .models import AttendanceRecord


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ("enrollment_subject", "class_date", "status", "marked_by")
    list_filter = ("status", "class_date")
    search_fields = (
        "enrollment_subject__enrollment__student__student_id",
        "enrollment_subject__enrollment__student__last_name",
    )
