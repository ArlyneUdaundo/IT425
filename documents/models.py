from django.conf import settings
from django.db import models


class StudentDocument(models.Model):
    class Type(models.TextChoices):
        REGISTRATION = "registration", "Certificate of Registration"
        INFORMATION_SHEET = "information_sheet", "Student Information Sheet"
        REPORT_OF_GRADES = "report_of_grades", "Report of Grades"
        TRANSCRIPT = "transcript", "Transcript of Records"
        ENROLLMENT = "enrollment", "Certificate of Enrollment"
        GOOD_MORAL = "good_moral", "Certificate of Good Moral Character"
        CLEARANCE = "clearance", "Student Clearance"

    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        ISSUED = "issued", "Issued"
        REJECTED = "rejected", "Rejected"

    student = models.ForeignKey(
        "students.Student", on_delete=models.PROTECT, related_name="documents"
    )
    document_type = models.CharField(max_length=24, choices=Type.choices)
    document_number = models.CharField(max_length=32, unique=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.REQUESTED
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    issued_at = models.DateTimeField(null=True, blank=True)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    notes = models.CharField(max_length=240, blank=True)

    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return f"{self.document_number}: {self.get_document_type_display()}"
