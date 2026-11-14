from django.contrib import admin

from .models import Grade, GradeHistory


class GradeHistoryInline(admin.TabularInline):
    model = GradeHistory
    extra = 0
    can_delete = False
    readonly_fields = ("midterm_grade", "final_grade", "remarks", "changed_by", "changed_at")


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ("enrollment_subject", "midterm_grade", "final_grade", "updated_by")
    list_filter = ("enrollment_subject__enrollment__semester",)
    inlines = [GradeHistoryInline]
