from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

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

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "first_name", "last_name", "email")


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = [
            "student_id",
            "first_name",
            "last_name",
            "email",
            "phone",
            "date_of_birth",
            "gender",
            "course",
            "enrollment_date",
            "address",
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


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ["code", "name", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ["code", "name", "course", "instructors"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instructor_ids = UserProfile.objects.filter(
            role=UserProfile.Role.INSTRUCTOR
        ).values_list("user_id", flat=True)
        self.fields["instructors"].queryset = self.fields[
            "instructors"
        ].queryset.filter(pk__in=instructor_ids)
