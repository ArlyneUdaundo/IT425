from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from academics.models import SectionSubject
from audit_logs.models import AuditLog
from audit_logs.services import record_activity
from enrollment.models import Enrollment, EnrollmentSubject
from students.models import UserProfile
from students.views import current_role, role_required

from .forms import AttendanceDateForm, AttendanceEntryForm
from .models import AttendanceRecord


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
def mark_attendance(request, pk):
    class_subject = _assigned_class_subject(request, pk)
    if class_subject is None:
        return HttpResponseForbidden("You do not have permission to manage this class.")

    enrolled_subjects = list(
        EnrollmentSubject.objects.filter(
            class_subject=class_subject,
            enrollment__status=Enrollment.Status.APPROVED,
        )
        .select_related("enrollment__student")
        .order_by("enrollment__student__last_name", "enrollment__student__first_name")
    )
    date_form = AttendanceDateForm(request.POST or None)
    attendance_date = None
    entry_forms = []
    if request.method == "POST":
        entry_forms = [
            (item, AttendanceEntryForm(request.POST, prefix=str(item.pk)))
            for item in enrolled_subjects
        ]
        if date_form.is_valid() and all(form.is_valid() for _, form in entry_forms):
            attendance_date = date_form.cleaned_data["class_date"]
            with transaction.atomic():
                for item, form in entry_forms:
                    status = form.cleaned_data["status"]
                    if not status:
                        continue
                    record, created = AttendanceRecord.objects.update_or_create(
                        enrollment_subject=item,
                        class_date=attendance_date,
                        defaults={
                            "status": status,
                            "notes": form.cleaned_data["notes"],
                            "marked_by": request.user,
                        },
                    )
                    record_activity(
                        actor=request.user,
                        action=(
                            AuditLog.Action.CREATE if created else AuditLog.Action.UPDATE
                        ),
                        entity=record,
                        description=(
                            f"Attendance {record.get_status_display().lower()} recorded "
                            f"for {item.enrollment.student.student_id} on {attendance_date}."
                        ),
                        request=request,
                    )
            messages.success(request, "Attendance was saved.")
            return redirect("attendance:mark", pk=class_subject.pk)
    else:
        requested_date = request.GET.get("class_date")
        date_form = (
            AttendanceDateForm({"class_date": requested_date})
            if requested_date
            else AttendanceDateForm()
        )
        if requested_date:
            attendance_date = (
                date_form.cleaned_data["class_date"]
                if date_form.is_valid()
                else None
            )
        else:
            attendance_date = timezone.localdate()
            date_form = AttendanceDateForm(initial={"class_date": attendance_date})
        entry_forms = []
        for item in enrolled_subjects:
            existing = None
            if attendance_date:
                existing = AttendanceRecord.objects.filter(
                    enrollment_subject=item, class_date=attendance_date
                ).first()
            entry_forms.append(
                (
                    item,
                    AttendanceEntryForm(
                        prefix=str(item.pk),
                        initial={
                            "status": existing.status if existing else "",
                            "notes": existing.notes if existing else "",
                        },
                    ),
                )
            )

    return render(
        request,
        "attendance/attendance_roster.html",
        {
            "class_subject": class_subject,
            "enrolled_subjects": enrolled_subjects,
            "date_form": date_form,
            "entry_forms": entry_forms,
            "attendance_date": attendance_date,
        },
    )
