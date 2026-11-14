from django.contrib import messages
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from academics.models import ClassSection
from audit_logs.models import AuditLog
from audit_logs.services import record_activity
from students.models import Student, UserProfile
from students.views import role_required

from .forms import EnrollmentCreateForm, StudentEnrollmentRequestForm
from .models import Enrollment, EnrollmentSubject


@role_required(UserProfile.Role.REGISTRAR)
def enrollment_list(request):
    enrollments = Enrollment.objects.select_related(
        "student", "student__course", "semester", "semester__academic_year", "section"
    ).prefetch_related("subjects")
    status = request.GET.get("status", "")
    if status in Enrollment.Status.values:
        enrollments = enrollments.filter(status=status)
    return render(
        request,
        "enrollment/enrollment_list.html",
        {
            "enrollments": enrollments,
            "statuses": Enrollment.Status.choices,
            "selected_status": status,
        },
    )


@role_required(UserProfile.Role.REGISTRAR)
def enrollment_create(request):
    if request.method == "POST":
        form = EnrollmentCreateForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    enrollment = form.save()
                    for class_subject in enrollment.section.class_subjects.all():
                        EnrollmentSubject.objects.create(
                            enrollment=enrollment, class_subject=class_subject
                        )
            except IntegrityError:
                form.add_error(
                    "student",
                    "An enrollment already exists for that student and semester.",
                )
            else:
                record_activity(
                    actor=request.user,
                    action=AuditLog.Action.CREATE,
                    entity=enrollment,
                    description=f"Enrollment created for {enrollment.student.student_id}.",
                    request=request,
                )
                messages.success(request, "Enrollment assessment was created.")
                return redirect("enrollment:list")
    else:
        form = EnrollmentCreateForm()
    return render(
        request,
        "enrollment/enrollment_form.html",
        {"form": form, "student_request": False},
    )


@role_required(UserProfile.Role.STUDENT)
def student_enrollment_request(request):
    student = Student.objects.filter(user=request.user, is_archived=False).first()
    if not student:
        messages.error(request, "Your account is not linked to an active student record.")
        return redirect("students:student_dashboard")
    if request.method == "POST":
        form = StudentEnrollmentRequestForm(request.POST, student=student)
        if form.is_valid():
            section = form.cleaned_data["section"]
            try:
                with transaction.atomic():
                    enrollment = Enrollment.objects.create(
                        student=student,
                        semester=section.semester,
                        section=section,
                    )
                    for class_subject in section.class_subjects.all():
                        EnrollmentSubject.objects.create(
                            enrollment=enrollment, class_subject=class_subject
                        )
            except IntegrityError:
                form.add_error("section", "An enrollment already exists for this semester.")
            else:
                record_activity(
                    actor=request.user,
                    action=AuditLog.Action.CREATE,
                    entity=enrollment,
                    description=f"Enrollment requested for {student.student_id}.",
                    request=request,
                )
                messages.success(request, "Your enrollment request was submitted.")
                return redirect("students:student_dashboard")
    else:
        form = StudentEnrollmentRequestForm(student=student)
    return render(
        request,
        "enrollment/enrollment_form.html",
        {"form": form, "student_request": True},
    )


@role_required(UserProfile.Role.REGISTRAR)
def decide_enrollment(request, pk):
    if request.method != "POST":
        return redirect("enrollment:list")
    action = request.POST.get("action")
    if action not in {"approve", "reject"}:
        messages.error(request, "Choose a valid enrollment decision.")
        return redirect("enrollment:list")

    with transaction.atomic():
        enrollment = get_object_or_404(
            Enrollment.objects.select_for_update().select_related("section"), pk=pk
        )
        if enrollment.status != Enrollment.Status.PENDING:
            messages.error(request, "Only pending enrollments can be assessed.")
            return redirect("enrollment:list")
        if action == "approve":
            section = get_object_or_404(
                ClassSection.objects.select_for_update(), pk=enrollment.section_id
            )
            enrolled_count = Enrollment.objects.filter(
                section=section, status=Enrollment.Status.APPROVED
            ).count()
            if enrolled_count >= section.capacity:
                messages.error(request, "This section has reached its enrollment capacity.")
                return redirect("enrollment:list")
            enrollment.status = Enrollment.Status.APPROVED
            audit_action = AuditLog.Action.APPROVE
            description = f"Enrollment approved for {enrollment.student.student_id}."
        else:
            enrollment.status = Enrollment.Status.REJECTED
            audit_action = AuditLog.Action.REJECT
            description = f"Enrollment rejected for {enrollment.student.student_id}."
        enrollment.assessed_by = request.user
        enrollment.assessed_at = timezone.now()
        enrollment.save(update_fields=["status", "assessed_by", "assessed_at"])
        record_activity(
            actor=request.user,
            action=audit_action,
            entity=enrollment,
            description=description,
            request=request,
        )

    messages.success(request, "Enrollment assessment was recorded.")
    return redirect("enrollment:list")
