from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class Course(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.SET_NULL,
        related_name="courses",
        null=True,
        blank=True,
    )
    duration_years = models.PositiveSmallIntegerField(
        default=4, validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    is_archived = models.BooleanField(default=False)
    is_generated = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class Subject(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    units = models.DecimalField(max_digits=4, decimal_places=1, default=3)
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="subjects"
    )
    prerequisites = models.ManyToManyField("self", blank=True, symmetrical=False)
    instructors = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="teaching_subjects"
    )
    is_archived = models.BooleanField(default=False)
    is_generated = models.BooleanField(default=False)

    class Meta:
        ordering = ["course__name", "name"]
        unique_together = [("course", "name")]

    def __str__(self):
        return f"{self.code} — {self.name}"


class UserProfile(models.Model):
    class Role(models.TextChoices):
        REGISTRAR = "registrar", "Registrar"
        INSTRUCTOR = "instructor", "Instructor"
        STUDENT = "student", "Student"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    role = models.CharField(max_length=20, choices=Role.choices)

    def __str__(self):
        return f"{self.user.get_username()} — {self.get_role_display()}"


class Student(models.Model):
    class Gender(models.TextChoices):
        FEMALE = "F", "Female"
        MALE = "M", "Male"
        NON_BINARY = "N", "Non-binary"
        PREFER_NOT_TO_SAY = "P", "Prefer not to say"

    class CivilStatus(models.TextChoices):
        SINGLE = "single", "Single"
        MARRIED = "married", "Married"
        WIDOWED = "widowed", "Widowed"
        SEPARATED = "separated", "Separated"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ON_LEAVE = "on_leave", "On leave"
        SUSPENDED = "suspended", "Suspended"
        GRADUATED = "graduated", "Graduated"
        WITHDRAWN = "withdrawn", "Withdrawn"

    student_id = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=80)
    middle_name = models.CharField(max_length=80, blank=True, default="")
    last_name = models.CharField(max_length=80)
    suffix = models.CharField(max_length=20, blank=True, default="")
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, blank=True)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=Gender.choices, blank=True)
    civil_status = models.CharField(
        max_length=12, choices=CivilStatus.choices, blank=True, default=""
    )
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="students")
    enrollment_date = models.DateField()
    address = models.TextField(blank=True)
    emergency_contact_name = models.CharField(max_length=160, blank=True, default="")
    emergency_contact_phone = models.CharField(max_length=30, blank=True, default="")
    guardian_name = models.CharField(max_length=160, blank=True, default="")
    guardian_relationship = models.CharField(max_length=40, blank=True, default="")
    guardian_phone = models.CharField(max_length=30, blank=True, default="")
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.ACTIVE
    )
    is_archived = models.BooleanField(default=False)
    is_generated = models.BooleanField(default=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="student_record",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.student_id})"

    @property
    def full_name(self):
        names = [self.first_name, self.middle_name, self.last_name, self.suffix]
        return " ".join(name for name in names if name)

    @property
    def age(self):
        today = timezone.localdate()
        return (
            today.year
            - self.date_of_birth.year
            - (
                (today.month, today.day)
                < (self.date_of_birth.month, self.date_of_birth.day)
            )
        )
