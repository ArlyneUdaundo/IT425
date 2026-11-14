from django.contrib import admin

from .models import Enrollment, EnrollmentSubject


class EnrollmentSubjectInline(admin.TabularInline):
    model = EnrollmentSubject
    extra = 0


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "semester", "section", "status", "enrolled_at")
    list_filter = ("status", "semester")
    search_fields = ("student__student_id", "student__first_name", "student__last_name")
    inlines = [EnrollmentSubjectInline]
