from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Enrollment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending assessment"
        APPROVED = "approved", "Enrolled"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    student = models.ForeignKey(
        "students.Student", on_delete=models.PROTECT, related_name="enrollments"
    )
    semester = models.ForeignKey(
        "academics.Semester", on_delete=models.PROTECT, related_name="enrollments"
    )
    section = models.ForeignKey(
        "academics.ClassSection",
        on_delete=models.PROTECT,
        related_name="enrollments",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDING
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="assessed_enrollments",
        null=True,
        blank=True,
    )
    assessed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    is_generated = models.BooleanField(default=False)

    class Meta:
        ordering = ["-semester__academic_year__start_date", "student__last_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "semester"], name="one_enrollment_per_student_term"
            )
        ]

    def clean(self):
        if self.student_id and self.student.is_archived:
            raise ValidationError({"student": "Archived students cannot enroll."})
        if self.section_id and self.semester_id:
            if self.section.semester_id != self.semester_id:
                raise ValidationError(
                    {"section": "Section must belong to this semester."}
                )
        if self.section_id and self.student_id:
            if self.section.course_id != self.student.course_id:
                raise ValidationError(
                    {"section": "Section must match the student's course."}
                )

    def __str__(self):
        return f"{self.student.student_id} — {self.semester}"


class EnrollmentSubject(models.Model):
    enrollment = models.ForeignKey(
        Enrollment, on_delete=models.CASCADE, related_name="subjects"
    )
    class_subject = models.ForeignKey(
        "academics.SectionSubject",
        on_delete=models.PROTECT,
        related_name="enrollment_subjects",
    )
    is_generated = models.BooleanField(default=False)

    class Meta:
        ordering = ["class_subject__subject__code"]
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment", "class_subject"],
                name="unique_enrolled_class_subject",
            )
        ]

    def clean(self):
        if self.enrollment_id and self.class_subject_id:
            if self.enrollment.section_id != self.class_subject.section_id:
                raise ValidationError(
                    {"class_subject": "Subject must be offered by the enrolled section."}
                )

    def __str__(self):
        return f"{self.enrollment}: {self.class_subject.subject}"

    @property
    def attendance_percentage(self):
        records = [
            record
            for record in self.attendance_records.all()
            if record.status != "excused"
        ]
        if not records:
            return None
        attended = sum(
            record.status
            in {
                record.Status.PRESENT,
                record.Status.LATE,
            }
            for record in records
        )
        return round(attended * 100 / len(records), 1)
