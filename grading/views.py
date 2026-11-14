from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from academics.models import SectionSubject
from audit_logs.models import AuditLog
from audit_logs.services import record_activity
from enrollment.models import Enrollment, EnrollmentSubject
from students.models import UserProfile
from students.views import current_role, role_required

from .forms import GradeForm
from .models import Grade, GradeHistory


def _assigned_class_subject(request, pk):
    query = SectionSubject.objects.select_related(
        "subject", "section", "instructor__user"
    )
    if current_role(request.user) == UserProfile.Role.REGISTRAR:
        return get_object_or_404(query, pk=pk)
    if current_role(request.user) == UserProfile.Role.INSTRUCTOR:
        return get_object_or_404(query, pk=pk, instructor__user=request.user)
    return None


@role_required(UserProfile.Role.REGISTRAR, UserProfile.Role.INSTRUCTOR)
def grade_roster(request, pk):
    class_subject = _assigned_class_subject(request, pk)
    if class_subject is None:
        return HttpResponseForbidden("You do not have permission to view this class.")
    enrolled_subjects = (
        EnrollmentSubject.objects.filter(
            class_subject=class_subject,
            enrollment__status=Enrollment.Status.APPROVED,
        )
        .select_related("enrollment__student", "grade")
        .order_by("enrollment__student__last_name", "enrollment__student__first_name")
    )
    return render(
        request,
        "grading/grade_roster.html",
        {"class_subject": class_subject, "enrolled_subjects": enrolled_subjects},
    )


@role_required(UserProfile.Role.REGISTRAR, UserProfile.Role.INSTRUCTOR)
def grade_update(request, pk):
    enrollment_subject = get_object_or_404(
        EnrollmentSubject.objects.select_related(
            "class_subject__instructor__user",
            "class_subject__subject",
            "enrollment__student",
        ),
        pk=pk,
        enrollment__status=Enrollment.Status.APPROVED,
    )
    if current_role(request.user) != UserProfile.Role.REGISTRAR and (
        enrollment_subject.class_subject.instructor is None
        or enrollment_subject.class_subject.instructor.user_id != request.user.pk
    ):
        return HttpResponseForbidden("You may only edit grades for your assigned classes.")

    grade = Grade.objects.filter(enrollment_subject=enrollment_subject).first()
    if request.method == "POST":
        form = GradeForm(request.POST, instance=grade)
        if form.is_valid():
            with transaction.atomic():
                grade, created = Grade.objects.select_for_update().get_or_create(
                    enrollment_subject=enrollment_subject
                )
                changed = (
                    grade.midterm_grade != form.cleaned_data["midterm_grade"]
                    or grade.final_grade != form.cleaned_data["final_grade"]
                    or grade.remarks != form.cleaned_data["remarks"]
                )
                if changed:
                    if not created:
                        GradeHistory.objects.create(
                            grade=grade,
                            midterm_grade=grade.midterm_grade,
                            final_grade=grade.final_grade,
                            remarks=grade.remarks,
                            changed_by=request.user,
                        )
                    grade.midterm_grade = form.cleaned_data["midterm_grade"]
                    grade.final_grade = form.cleaned_data["final_grade"]
                    grade.remarks = form.cleaned_data["remarks"]
                    grade.updated_by = request.user
                    grade.save()
                    record_activity(
                        actor=request.user,
                        action=(
                            AuditLog.Action.CREATE if created else AuditLog.Action.UPDATE
                        ),
                        entity=grade,
                        description=f"Grade updated for {enrollment_subject.enrollment.student.student_id} in {enrollment_subject.class_subject.subject.code}.",
                        request=request,
                    )
            messages.success(request, "Grade saved.")
            return redirect(
                "grading:roster", pk=enrollment_subject.class_subject_id
            )
    else:
        form = GradeForm(instance=grade)
    return render(
        request,
        "grading/grade_form.html",
        {"form": form, "enrollment_subject": enrollment_subject, "grade": grade},
    )
