from django import forms

from .models import Grade


class GradeForm(forms.ModelForm):
    class Meta:
        model = Grade
        fields = ["midterm_grade", "final_grade", "remarks"]
        widgets = {
            "midterm_grade": forms.NumberInput(attrs={"min": "0", "max": "100", "step": "0.01"}),
            "final_grade": forms.NumberInput(attrs={"min": "0", "max": "100", "step": "0.01"}),
            "remarks": forms.TextInput(attrs={"maxlength": 240}),
        }
