from uuid import uuid4

from django.contrib import messages
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from audit_logs.models import AuditLog
from audit_logs.services import record_activity
from students.models import Student
from students.views import role_required

from .forms import AdmissionApplicationForm
from .models import AdmissionApplication


def apply(request):
    if request.method == "POST":
        form = AdmissionApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.application_number = (
                f"ADM-{timezone.localdate():%Y}-{uuid4().hex[:8].upper()}"
            )
            application.save()
            record_activity(
                actor=request.user,
                action=AuditLog.Action.CREATE,
                entity=application,
                description=f"Admission application {application.application_number} submitted.",
                request=request,
            )
            return render(
                request,
                "admissions/application_submitted.html",
                {"application": application},
            )
    else:
        form = AdmissionApplicationForm()
    return render(request, "admissions/application_form.html", {"form": form})


@role_required("registrar")
def application_list(request):
    applications = AdmissionApplication.objects.select_related(
        "preferred_course", "reviewed_by", "student"
    )
    status = request.GET.get("status", "")
    if status in AdmissionApplication.Status.values:
        applications = applications.filter(status=status)
    return render(
        request,
        "admissions/application_list.html",
        {
            "applications": applications,
            "statuses": AdmissionApplication.Status.choices,
            "selected_status": status,
        },
    )


@role_required("registrar")
def review_application(request, pk):
    if request.method != "POST":
        return redirect("admissions:list")

    action = request.POST.get("action")
    review_notes = request.POST.get("review_notes", "").strip()
    if action not in {"approve", "reject", "review"}:
        messages.error(request, "Choose a valid application decision.")
        return redirect("admissions:list")

    with transaction.atomic():
        application = get_object_or_404(
            AdmissionApplication.objects.select_for_update(), pk=pk
        )
        if application.status in {
            AdmissionApplication.Status.APPROVED,
            AdmissionApplication.Status.REJECTED,
        }:
            messages.error(request, "This application has already been decided.")
            return redirect("admissions:list")

        if action == "approve":
            if Student.objects.filter(email__iexact=application.email).exists():
                messages.error(
                    request,
                    "A student record already uses this email. Resolve the duplicate before approval.",
                )
                return redirect("admissions:list")
            student_id = f"EDU-{timezone.localdate():%Y}-{application.pk:06d}"
            if Student.objects.filter(student_id=student_id).exists():
                messages.error(
                    request,
                    "Could not generate a unique student ID. Contact system support.",
                )
                return redirect("admissions:list")
            try:
                with transaction.atomic():
                    student = Student.objects.create(
                        student_id=student_id,
                        first_name=application.first_name,
                        middle_name=application.middle_name,
                        last_name=application.last_name,
                        suffix=application.suffix,
                        email=application.email,
                        phone=application.phone,
                        date_of_birth=application.date_of_birth,
                        address=application.address,
                        course=application.preferred_course,
                        enrollment_date=timezone.localdate(),
                    )
            except IntegrityError:
                messages.error(
                    request,
                    "The student record conflicts with an existing record; resolve it before approval.",
                )
                return redirect("admissions:list")
            application.student = student
            application.status = AdmissionApplication.Status.APPROVED
            audit_action = AuditLog.Action.APPROVE
            description = (
                f"Admission {application.application_number} approved; "
                f"student record {student.student_id} created."
            )
        elif action == "reject":
            application.status = AdmissionApplication.Status.REJECTED
            audit_action = AuditLog.Action.REJECT
            description = f"Admission application {application.application_number} rejected."
        else:
            application.status = AdmissionApplication.Status.UNDER_REVIEW
            audit_action = AuditLog.Action.UPDATE
            description = f"Admission application {application.application_number} moved under review."
        application.review_notes = review_notes
        application.reviewed_by = request.user
        application.reviewed_at = timezone.now()
        application.save(
            update_fields=[
                "student",
                "status",
                "review_notes",
                "reviewed_by",
                "reviewed_at",
            ]
        )
        record_activity(
            actor=request.user,
            action=audit_action,
            entity=application,
            description=description,
            request=request,
        )

    messages.success(request, "Admission application updated.")
    return redirect("admissions:list")
