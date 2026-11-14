from django.conf import settings
from django.db import models


class FacultyProfile(models.Model):
    class EmploymentStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        ON_LEAVE = "on_leave", "On leave"
        INACTIVE = "inactive", "Inactive"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="faculty_profile",
    )
    faculty_id = models.CharField(max_length=20, unique=True)
    department = models.ForeignKey(
        "departments.Department", on_delete=models.PROTECT, related_name="faculty"
    )
    specialization = models.CharField(max_length=160, blank=True)
    contact_number = models.CharField(max_length=30, blank=True)
    employment_status = models.CharField(
        max_length=12,
        choices=EmploymentStatus.choices,
        default=EmploymentStatus.ACTIVE,
    )
    is_generated = models.BooleanField(default=False)

    class Meta:
        ordering = ["user__last_name", "user__first_name"]

    def __str__(self):
        return f"{self.faculty_id} — {self.user.get_full_name() or self.user.username}"
