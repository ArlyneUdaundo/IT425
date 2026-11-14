from django.conf import settings
from django.db import models


class AttendanceRecord(models.Model):
    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"
        LATE = "late", "Late"
        EXCUSED = "excused", "Excused"

    enrollment_subject = models.ForeignKey(
        "enrollment.EnrollmentSubject",
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    class_date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices)
    notes = models.CharField(max_length=240, blank=True)
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    marked_at = models.DateTimeField(auto_now=True)
    is_generated = models.BooleanField(default=False)

    class Meta:
        ordering = ["-class_date", "enrollment_subject__enrollment__student__last_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["enrollment_subject", "class_date"],
                name="one_attendance_record_per_class_day",
            )
        ]

    def __str__(self):
        return f"{self.enrollment_subject} — {self.class_date}: {self.get_status_display()}"
