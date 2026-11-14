from django import forms
from django.core.exceptions import ValidationError

from academics.models import ClassSection
from students.models import Student

from .models import Enrollment


class EnrollmentCreateForm(forms.ModelForm):
    class Meta:
        model = Enrollment
        fields = ["student", "section", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["student"].queryset = Student.objects.filter(
            is_archived=False
        ).select_related("course")
        self.fields["section"].queryset = ClassSection.objects.filter(
            is_active=True, semester__is_active=True
        ).select_related("course", "semester")

    def clean(self):
        cleaned_data = super().clean()
        student = cleaned_data.get("student")
        section = cleaned_data.get("section")
        if student and section and student.course_id != section.course_id:
            self.add_error("section", "Choose a section from the student's course.")
        if student and section and Enrollment.objects.filter(
            student=student, semester=section.semester
        ).exists():
            self.add_error(
                "student", "This student already has an enrollment for that semester."
            )
        return cleaned_data

    def save(self, commit=True):
        enrollment = super().save(commit=False)
        enrollment.semester = self.cleaned_data["section"].semester
        if commit:
            enrollment.save()
        return enrollment


class StudentEnrollmentRequestForm(forms.Form):
    section = forms.ModelChoiceField(
        queryset=ClassSection.objects.none(), label="Section"
    )

    def __init__(self, *args, student, **kwargs):
        super().__init__(*args, **kwargs)
        self.student = student
        self.fields["section"].queryset = ClassSection.objects.filter(
            course=student.course,
            is_active=True,
            semester__is_active=True,
        ).select_related("course", "semester")

    def clean_section(self):
        section = self.cleaned_data["section"]
        if Enrollment.objects.filter(
            student=self.student, semester=section.semester
        ).exists():
            raise ValidationError("You already have an enrollment for this semester.")
        return section
