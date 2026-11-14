from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Grade(models.Model):
    enrollment_subject = models.OneToOneField(
        "enrollment.EnrollmentSubject",
        on_delete=models.CASCADE,
        related_name="grade",
    )
    midterm_grade = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    final_grade = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    remarks = models.CharField(max_length=240, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    updated_at = models.DateTimeField(auto_now=True)
    is_generated = models.BooleanField(default=False)

    class Meta:
        ordering = ["enrollment_subject__enrollment__student__last_name"]

    @property
    def computed_final_grade(self):
        if self.midterm_grade is None or self.final_grade is None:
            return None
        return (self.midterm_grade + self.final_grade) / 2

    @property
    def standing(self):
        computed = self.computed_final_grade
        if computed is None:
            return "Incomplete"
        return "Passed" if computed >= 75 else "Failed"

    def __str__(self):
        return f"Grade: {self.enrollment_subject}"


class GradeHistory(models.Model):
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name="history")
    midterm_grade = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    final_grade = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    remarks = models.CharField(max_length=240, blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    is_generated = models.BooleanField(default=False)

    class Meta:
        ordering = ["-changed_at"]
