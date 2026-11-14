from django.contrib import admin

from .models import FacultyProfile


@admin.register(FacultyProfile)
class FacultyProfileAdmin(admin.ModelAdmin):
    list_display = ("faculty_id", "user", "department", "employment_status")
    list_filter = ("department", "employment_status")
    search_fields = ("faculty_id", "user__first_name", "user__last_name", "user__email")
