from django.contrib import admin

from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("student_id", "last_name", "first_name", "course", "email")
    list_filter = ("course", "gender", "enrollment_date")
    search_fields = ("student_id", "first_name", "last_name", "email", "course")
    ordering = ("last_name", "first_name")
