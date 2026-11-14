from django.contrib import admin

from .models import (
    AcademicYear,
    ClassSchedule,
    ClassSection,
    Curriculum,
    CurriculumSubject,
    SectionSubject,
    Semester,
)

admin.site.register(AcademicYear)
admin.site.register(Semester)
admin.site.register(Curriculum)
admin.site.register(CurriculumSubject)
admin.site.register(ClassSection)
admin.site.register(SectionSubject)
admin.site.register(ClassSchedule)
