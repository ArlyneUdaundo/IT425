from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from departments.models import Department
from faculty.models import FacultyProfile

from .models import Course, Student, Subject, UserProfile


class StudentSignupForm(UserCreationForm):
    student_id = forms.CharField(max_length=20, label="Student ID")
    email = forms.EmailField()

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields(
            ["student_id", "email", "username", "password1", "password2"]
        )

    def clean(self):
        cleaned_data = super().clean()
        student_id = cleaned_data.get("student_id")
        email = cleaned_data.get("email")
        if student_id and email and not Student.objects.filter(
            student_id=student_id,
            email__iexact=email,
            user__isnull=True,
        ).exists():
            raise forms.ValidationError(
                "No unlinked student record matches that student ID and email. "
                "Check your details or contact the registrar."
            )
        return cleaned_data


class StaffAccountForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=[
            (UserProfile.Role.REGISTRAR, "Registrar"),
            (UserProfile.Role.INSTRUCTOR, "Instructor"),
        ]
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.none(), required=False
    )
    faculty_id = forms.CharField(max_length=20, required=False, label="Faculty ID")
    specialization = forms.CharField(max_length=160, required=False)
    contact_number = forms.CharField(max_length=30, required=False)

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "first_name", "last_name", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].queryset = Department.objects.filter(is_active=True)
        self.order_fields(
            [
                "role",
                "username",
                "first_name",
                "last_name",
                "email",
                "department",
                "faculty_id",
                "specialization",
                "contact_number",
                "password1",
                "password2",
            ]
        )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("role") == UserProfile.Role.INSTRUCTOR:
            for field in ("department", "faculty_id"):
                if not cleaned_data.get(field):
                    self.add_error(field, "This field is required for instructor accounts.")
            faculty_id = cleaned_data.get("faculty_id")
            if faculty_id and FacultyProfile.objects.filter(faculty_id=faculty_id).exists():
                self.add_error("faculty_id", "This faculty ID is already in use.")
        return cleaned_data


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            "student_id",
            "first_name",
            "middle_name",
            "last_name",
            "suffix",
            "email",
            "phone",
            "date_of_birth",
            "gender",
            "civil_status",
            "course",
            "enrollment_date",
            "address",
            "emergency_contact_name",
            "emergency_contact_phone",
            "guardian_name",
            "guardian_relationship",
            "guardian_phone",
            "status",
            "user",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "enrollment_date": forms.DateInput(attrs={"type": "date"}),
            "address": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        student_ids = UserProfile.objects.filter(
            role=UserProfile.Role.STUDENT
        ).values_list("user_id", flat=True)
        self.fields["user"].queryset = get_user_model().objects.filter(
            pk__in=student_ids
        ).order_by("username")
        self.fields["user"].required = False
        self.fields["status"].required = False
        if not self.instance.pk:
            self.fields["status"].initial = Student.Status.ACTIVE


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["code", "name", "department", "duration_years", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["department"].required = False
        self.fields["duration_years"].required = False


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = [
            "code",
            "name",
            "description",
            "units",
            "course",
            "prerequisites",
            "instructors",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["units"].required = False
        instructor_ids = UserProfile.objects.filter(
            role=UserProfile.Role.INSTRUCTOR
        ).values_list("user_id", flat=True)
        self.fields["instructors"].queryset = self.fields[
            "instructors"
        ].queryset.filter(pk__in=instructor_ids)
