from django import forms

from students.models import Course

from .models import AdmissionApplication


class AdmissionApplicationForm(forms.ModelForm):
    class Meta:
        model = AdmissionApplication
        fields = [
            "first_name",
            "middle_name",
            "last_name",
            "suffix",
            "email",
            "phone",
            "date_of_birth",
            "address",
            "preferred_course",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "address": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["preferred_course"].queryset = Course.objects.filter(
            is_archived=False
        ).order_by("name")
