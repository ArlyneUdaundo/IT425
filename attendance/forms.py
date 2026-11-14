from django import forms
from django.utils import timezone

from .models import AttendanceRecord


class AttendanceDateForm(forms.Form):
    class_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        initial=timezone.localdate,
    )

    def clean_class_date(self):
        class_date = self.cleaned_data["class_date"]
        if class_date > timezone.localdate():
            raise forms.ValidationError("Attendance cannot be recorded for a future date.")
        return class_date


class AttendanceEntryForm(forms.Form):
    status = forms.ChoiceField(
        choices=[("", "No change"), *AttendanceRecord.Status.choices],
        required=False,
    )
    notes = forms.CharField(max_length=240, required=False)
