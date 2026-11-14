from django.contrib import admin

from .models import Course, Student, Subject, UserProfile


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "department",
        "duration_years",
        "is_archived",
        "is_generated",
    )
    list_filter = ("department", "is_archived", "is_generated")
    search_fields = ("code", "name", "department__name")


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "course", "units", "is_archived", "is_generated")
    list_filter = ("course", "is_archived", "is_generated")
    search_fields = ("code", "name", "course__name")
    filter_horizontal = ("instructors",)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role")
    list_filter = ("role",)
    search_fields = ("user__username", "user__email")


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        "student_id",
        "last_name",
        "first_name",
        "course",
        "status",
        "is_archived",
        "is_generated",
        "email",
        "user",
    )
    list_filter = (
        "course",
        "gender",
        "status",
        "is_archived",
        "is_generated",
        "enrollment_date",
    )
    search_fields = ("student_id", "first_name", "last_name", "email", "course")
    ordering = ("last_name", "first_name")
