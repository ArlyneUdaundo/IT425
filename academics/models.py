from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q


class AcademicYear(models.Model):
    name = models.CharField(max_length=20, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_generated = models.BooleanField(default=False)

    class Meta:
        ordering = ["-start_date"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gt=F("start_date")),
                name="academic_year_end_after_start",
            ),
            models.UniqueConstraint(
                fields=["is_current"],
                condition=Q(is_current=True),
                name="one_current_academic_year",
            ),
        ]

    def clean(self):
        if self.end_date <= self.start_date:
            raise ValidationError({"end_date": "End date must be after start date."})

    def __str__(self):
        return self.name


class Semester(models.Model):
    class Term(models.TextChoices):
        FIRST = "first", "First semester"
        SECOND = "second", "Second semester"
        SUMMER = "summer", "Summer"

    academic_year = models.ForeignKey(
        AcademicYear, on_delete=models.PROTECT, related_name="semesters"
    )
    term = models.CharField(max_length=10, choices=Term.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    is_generated = models.BooleanField(default=False)

    class Meta:
        ordering = ["-academic_year__start_date", "term"]
        constraints = [
            models.UniqueConstraint(
                fields=["academic_year", "term"], name="unique_term_per_academic_year"
            ),
            models.CheckConstraint(
                condition=Q(end_date__gt=F("start_date")),
                name="semester_end_after_start",
            ),
        ]

    def clean(self):
        errors = {}
        if self.end_date <= self.start_date:
            errors["end_date"] = "End date must be after start date."
        if self.academic_year_id and (
            self.start_date < self.academic_year.start_date
            or self.end_date > self.academic_year.end_date
        ):
            errors["academic_year"] = "Semester dates must fall within the academic year."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.get_term_display()} {self.academic_year.name}"


class Curriculum(models.Model):
    course = models.ForeignKey(
        "students.Course", on_delete=models.PROTECT, related_name="curricula"
    )
    name = models.CharField(max_length=120)
    effective_from = models.DateField()
    effective_until = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_generated = models.BooleanField(default=False)

    class Meta:
        ordering = ["course__name", "-effective_from"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "name"], name="unique_curriculum_name_per_course"
            ),
            models.CheckConstraint(
                condition=Q(effective_until__isnull=True)
                | Q(effective_until__gt=F("effective_from")),
                name="curriculum_end_after_start",
            ),
        ]

    def __str__(self):
        return f"{self.course.code} — {self.name}"


class CurriculumSubject(models.Model):
    curriculum = models.ForeignKey(
        Curriculum, on_delete=models.CASCADE, related_name="requirements"
    )
    subject = models.ForeignKey(
        "students.Subject", on_delete=models.PROTECT, related_name="curriculum_entries"
    )
    semester = models.ForeignKey(
        Semester, on_delete=models.PROTECT, related_name="curriculum_entries"
    )
    year_level = models.PositiveSmallIntegerField()
    units = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    is_generated = models.BooleanField(default=False)

    class Meta:
        ordering = ["year_level", "semester__term", "subject__code"]
        constraints = [
            models.UniqueConstraint(
                fields=["curriculum", "subject"], name="unique_subject_per_curriculum"
            ),
            models.CheckConstraint(
                condition=Q(year_level__gte=1), name="curriculum_year_level_positive"
            ),
        ]

    def clean(self):
        if self.curriculum_id and self.subject_id:
            if self.curriculum.course_id != self.subject.course_id:
                raise ValidationError(
                    {"subject": "Subject must belong to the curriculum course."}
                )

    def __str__(self):
        return f"{self.curriculum}: {self.subject}"


class ClassSection(models.Model):
    course = models.ForeignKey(
        "students.Course", on_delete=models.PROTECT, related_name="sections"
    )
    semester = models.ForeignKey(
        Semester, on_delete=models.PROTECT, related_name="sections"
    )
    name = models.CharField(max_length=40)
    year_level = models.PositiveSmallIntegerField()
    capacity = models.PositiveSmallIntegerField(default=40)
    is_active = models.BooleanField(default=True)
    is_generated = models.BooleanField(default=False)

    class Meta:
        ordering = ["course__code", "year_level", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "semester", "name"],
                name="unique_section_per_course_term",
            ),
            models.CheckConstraint(
                condition=Q(capacity__gte=1), name="section_capacity_positive"
            ),
            models.CheckConstraint(
                condition=Q(year_level__gte=1), name="section_year_level_positive"
            ),
        ]

    def __str__(self):
        return f"{self.course.code} {self.name} — {self.semester}"


class SectionSubject(models.Model):
    section = models.ForeignKey(
        ClassSection, on_delete=models.CASCADE, related_name="class_subjects"
    )
    subject = models.ForeignKey(
        "students.Subject", on_delete=models.PROTECT, related_name="class_sections"
    )
    instructor = models.ForeignKey(
        "faculty.FacultyProfile",
        on_delete=models.PROTECT,
        related_name="class_assignments",
        null=True,
        blank=True,
    )
    is_generated = models.BooleanField(default=False)

    class Meta:
        ordering = ["section", "subject__code"]
        constraints = [
            models.UniqueConstraint(
                fields=["section", "subject"], name="unique_subject_per_section"
            )
        ]

    def clean(self):
        if self.section_id and self.subject_id:
            if self.section.course_id != self.subject.course_id:
                raise ValidationError(
                    {"subject": "Subject must belong to the section course."}
                )
        if self.instructor_id and self.section_id:
            course_department_id = self.section.course.department_id
            faculty_department_id = self.instructor.department_id
            if (
                course_department_id
                and faculty_department_id != course_department_id
            ):
                raise ValidationError(
                    {"instructor": "Faculty member must belong to the course department."}
                )

    def __str__(self):
        return f"{self.section}: {self.subject}"


class ClassSchedule(models.Model):
    class Day(models.TextChoices):
        MONDAY = "mon", "Monday"
        TUESDAY = "tue", "Tuesday"
        WEDNESDAY = "wed", "Wednesday"
        THURSDAY = "thu", "Thursday"
        FRIDAY = "fri", "Friday"
        SATURDAY = "sat", "Saturday"
        SUNDAY = "sun", "Sunday"

    class_subject = models.ForeignKey(
        SectionSubject, on_delete=models.CASCADE, related_name="schedules"
    )
    day = models.CharField(max_length=3, choices=Day.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.CharField(max_length=40)
    is_generated = models.BooleanField(default=False)

    class Meta:
        ordering = ["day", "start_time"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_time__gt=F("start_time")),
                name="class_schedule_end_after_start",
            )
        ]

    def clean(self):
        if self.end_time <= self.start_time:
            raise ValidationError({"end_time": "End time must be after start time."})
        conflicts = ClassSchedule.objects.filter(
            day=self.day,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time,
        ).exclude(pk=self.pk)
        errors = {}
        if conflicts.filter(room=self.room).exists():
            errors["room"] = "This room is already scheduled during that time."
        if (
            self.class_subject_id
            and self.class_subject.instructor_id
            and conflicts.filter(
                class_subject__instructor=self.class_subject.instructor
            ).exists()
        ):
            errors["class_subject"] = "This faculty member already has a class during that time."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.get_day_display()} {self.start_time}-{self.end_time} ({self.room})"
