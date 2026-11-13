from django.conf import settings
from django.db import models


class Course(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class Subject(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=120)
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="subjects"
    )
    instructors = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name="teaching_subjects"
    )

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

    student_id = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, blank=True)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=Gender.choices, blank=True)
    course = models.ForeignKey(Course, on_delete=models.PROTECT, related_name="students")
    enrollment_date = models.DateField()
    address = models.TextField(blank=True)
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
        return f"{self.first_name} {self.last_name}"
