from django.http import HttpResponseForbidden
from django.shortcuts import render

from academics.models import SectionSubject
from students.models import UserProfile
from students.views import current_role, role_required


@role_required(UserProfile.Role.REGISTRAR, UserProfile.Role.INSTRUCTOR)
def class_list(request):
    assignments = SectionSubject.objects.select_related(
        "section__course",
        "section__semester__academic_year",
        "subject",
        "instructor__user",
    )
    if current_role(request.user) == UserProfile.Role.INSTRUCTOR:
        assignments = assignments.filter(instructor__user=request.user)
    elif current_role(request.user) != UserProfile.Role.REGISTRAR:
        return HttpResponseForbidden("You do not have permission to view classes.")
    return render(request, "faculty/class_list.html", {"assignments": assignments})
