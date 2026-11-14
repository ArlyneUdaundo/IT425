import csv
from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from datetime import timedelta
from admissions.models import AdmissionApplication
from audit_logs.models import AuditLog
from attendance.models import AttendanceRecord
from enrollment.models import Enrollment
from accounts.services import provision_registrar_access
from audit_logs.services import record_activity
from faculty.models import FacultyProfile
from grading.models import Grade

from .forms import (
    CourseForm,
    StaffAccountForm,
    StudentForm,
    StudentSignupForm,
    SubjectForm,
)
from .models import Course, Student, Subject, UserProfile


def current_role(user):
    if user.is_superuser:
        return UserProfile.Role.REGISTRAR
    return UserProfile.objects.filter(user=user).values_list("role", flat=True).first()


def role_required(*allowed_roles):
    def decorate(view):
        @wraps(view)
        @login_required
        def wrapped(request, *args, **kwargs):
            if current_role(request.user) not in allowed_roles:
                return HttpResponseForbidden("You do not have permission to access this page.")
            return view(request, *args, **kwargs)

        return wrapped

    return decorate


@login_required
def role_home(request):
    destinations = {
        UserProfile.Role.REGISTRAR: "students:registrar_dashboard",
        UserProfile.Role.INSTRUCTOR: "students:instructor_dashboard",
        UserProfile.Role.STUDENT: "students:student_dashboard",
    }
    destination = destinations.get(current_role(request.user))
    if not destination:
        return HttpResponseForbidden("Your account does not have an assigned role.")
    return redirect(destination)


@login_required
def account_detail(request):
    profile = UserProfile.objects.filter(user=request.user).first()
    student = Student.objects.select_related("course").filter(user=request.user).first()
    faculty = FacultyProfile.objects.select_related("department").filter(
        user=request.user
    ).first()
    if request.user.is_superuser:
        role_label = "System administrator"
    elif profile:
        role_label = profile.get_role_display()
    else:
        role_label = "Role not assigned"
    return render(
        request,
        "students/account_detail.html",
        {
            "account_user": request.user,
            "role_label": role_label,
            "student": student,
            "faculty": faculty,
        },
    )


def student_register(request):
    if request.user.is_authenticated:
        return redirect("students:home")
    if request.method == "POST":
        form = StudentSignupForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                student = Student.objects.select_for_update().filter(
                    student_id=form.cleaned_data["student_id"],
                    email__iexact=form.cleaned_data["email"],
                    user__isnull=True,
                ).first()
                if student is None:
                    form.add_error(
                        None,
                        "No unlinked student record matches that student ID and email. "
                        "Check your details or contact the registrar.",
                    )
                else:
                    user = form.save(commit=False)
                    user.first_name = student.first_name
                    user.last_name = student.last_name
                    user.email = student.email
                    user.save()
                    UserProfile.objects.create(
                        user=user, role=UserProfile.Role.STUDENT
                    )
                    student.user = user
                    student.save(update_fields=["user", "updated_at"])
            if student is not None:
                login(request, user)
                messages.success(request, "Your student account is ready.")
                return redirect("students:student_dashboard")
    else:
        form = StudentSignupForm()
    return render(request, "registration/student_register.html", {"form": form})


@role_required(UserProfile.Role.REGISTRAR)
def registrar_dashboard(request):
    month_ago = timezone.now() - timedelta(days=30)
    context = {
        "student_count": Student.objects.filter(is_archived=False).count(),
        "enrolled_count": Enrollment.objects.filter(
            status=Enrollment.Status.APPROVED
        ).count(),
        "new_admission_count": AdmissionApplication.objects.filter(
            submitted_at__gte=month_ago
        ).count(),
        "faculty_count": FacultyProfile.objects.filter(
            employment_status=FacultyProfile.EmploymentStatus.ACTIVE
        ).count(),
        "course_count": Course.objects.count(),
        "department_count": Course.objects.exclude(department=None)
        .values("department_id")
        .distinct()
        .count(),
        "subject_count": Subject.objects.count(),
        "male_student_count": Student.objects.filter(gender=Student.Gender.MALE).count(),
        "female_student_count": Student.objects.filter(
            gender=Student.Gender.FEMALE
        ).count(),
        "registrar_count": UserProfile.objects.filter(
            role=UserProfile.Role.REGISTRAR
        ).count(),
        "instructor_count": UserProfile.objects.filter(
            role=UserProfile.Role.INSTRUCTOR
        ).count(),
        "registrar_count": UserProfile.objects.filter(
            role=UserProfile.Role.REGISTRAR
        ).count(),
        "staff_profiles": UserProfile.objects.filter(
            role__in=[UserProfile.Role.REGISTRAR, UserProfile.Role.INSTRUCTOR]
        )
        .select_related("user")
        .order_by("role", "user__last_name", "user__first_name"),
        "recent_students": Student.objects.select_related("course")[:6],
        "recent_activities": AuditLog.objects.select_related("actor")[:8],
    }
    return render(request, "students/registrar_dashboard.html", context)


@role_required(UserProfile.Role.REGISTRAR)
def registrar_reports(request):
    return render(request, "students/registrar_reports.html")


@role_required(UserProfile.Role.REGISTRAR)
def registrar_report_export(request, report_type):
    report_specs = {
        "students": (
            ["Student ID", "Name", "Email", "Course", "Status", "Provenance"],
            Student.objects.filter(is_archived=False).select_related("course"),
        ),
        "enrollments": (
            [
                "Student ID",
                "Name",
                "Course",
                "Academic year",
                "Semester",
                "Section",
                "Status",
                "Provenance",
            ],
            Enrollment.objects.select_related(
                "student", "student__course", "semester__academic_year", "section"
            ),
        ),
        "grades": (
            [
                "Student ID",
                "Name",
                "Course",
                "Subject",
                "Midterm",
                "Final",
                "Computed final",
                "Standing",
                "Provenance",
            ],
            Grade.objects.select_related(
                "enrollment_subject__enrollment__student__course",
                "enrollment_subject__class_subject__subject",
            ),
        ),
        "attendance": (
            ["Student ID", "Name", "Course", "Subject", "Date", "Status", "Notes", "Provenance"],
            AttendanceRecord.objects.select_related(
                "enrollment_subject__enrollment__student__course",
                "enrollment_subject__class_subject__subject",
            ),
        ),
    }
    spec = report_specs.get(report_type)
    if spec is None:
        return HttpResponse("Unknown report.", status=404)

    headers, records = spec
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="educate-{report_type}.csv"'
    writer = csv.writer(response)
    writer.writerow(headers)
    for record in records.iterator():
        if report_type == "students":
            student = record
            row = [
                student.student_id,
                student.full_name,
                student.email,
                student.course.name,
                student.get_status_display(),
                "Generated - unverified" if student.is_generated else "Institutional",
            ]
        elif report_type == "enrollments":
            enrollment = record
            row = [
                enrollment.student.student_id,
                enrollment.student.full_name,
                enrollment.student.course.name,
                enrollment.semester.academic_year.name,
                enrollment.semester.get_term_display(),
                enrollment.section.name if enrollment.section else "",
                enrollment.get_status_display(),
                (
                    "Generated - unverified"
                    if enrollment.is_generated
                    else "Institutional"
                ),
            ]
        elif report_type == "grades":
            grade = record
            enrollment_subject = grade.enrollment_subject
            row = [
                enrollment_subject.enrollment.student.student_id,
                enrollment_subject.enrollment.student.full_name,
                enrollment_subject.enrollment.student.course.name,
                enrollment_subject.class_subject.subject.name,
                grade.midterm_grade,
                grade.final_grade,
                grade.computed_final_grade,
                grade.standing,
                "Generated - unverified" if grade.is_generated else "Institutional",
            ]
        else:
            attendance = record
            enrollment_subject = attendance.enrollment_subject
            row = [
                enrollment_subject.enrollment.student.student_id,
                enrollment_subject.enrollment.student.full_name,
                enrollment_subject.enrollment.student.course.name,
                enrollment_subject.class_subject.subject.name,
                attendance.class_date,
                attendance.get_status_display(),
                attendance.notes,
                "Generated - unverified" if attendance.is_generated else "Institutional",
            ]
        writer.writerow([
            (
                "'" + value
                if isinstance(value, str)
                and value.startswith(("=", "+", "-", "@", "\t", "\r"))
                else value
            )
            for value in row
        ])
    return response


@role_required(UserProfile.Role.REGISTRAR)
def staff_account_create(request):
    if request.method == "POST":
        form = StaffAccountForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save()
                UserProfile.objects.create(
                    user=user, role=form.cleaned_data["role"]
                )
                if form.cleaned_data["role"] == UserProfile.Role.REGISTRAR:
                    provision_registrar_access(user)
                elif form.cleaned_data["role"] == UserProfile.Role.INSTRUCTOR:
                    FacultyProfile.objects.create(
                        user=user,
                        faculty_id=form.cleaned_data["faculty_id"],
                        department=form.cleaned_data["department"],
                        specialization=form.cleaned_data["specialization"],
                        contact_number=form.cleaned_data["contact_number"],
                    )
            messages.success(
                request,
                f"The {form.cleaned_data['role']} account was created.",
            )
            return redirect("students:registrar_dashboard")
    else:
        form = StaffAccountForm()
    return render(
        request,
        "students/staff_account_form.html",
        {"form": form, "page_title": "Create staff account"},
    )


@role_required(UserProfile.Role.INSTRUCTOR)
def instructor_dashboard(request):
    subjects = (
        request.user.teaching_subjects.select_related("course")
        .annotate(student_count=Count("course__students", distinct=True))
        .all()
    )
    return render(request, "students/instructor_dashboard.html", {"subjects": subjects})


@role_required(UserProfile.Role.INSTRUCTOR)
def instructor_subject(request, pk):
    subject = get_object_or_404(
        request.user.teaching_subjects.select_related("course"), pk=pk
    )
    students = subject.course.students.select_related("course").all()
    return render(
        request,
        "students/instructor_subject.html",
        {"subject": subject, "students": students},
    )


@role_required(UserProfile.Role.STUDENT)
def student_dashboard(request):
    student = (
        Student.objects.select_related("course")
        .filter(user=request.user)
        .first()
    )
    subjects = (
        Subject.objects.filter(course=student.course, is_archived=False).prefetch_related(
            "instructors"
        )
        if student
        else Subject.objects.none()
    )
    enrollments = (
        Enrollment.objects.filter(student=student)
        .select_related("semester__academic_year", "section")
        .prefetch_related(
            "subjects__class_subject__subject",
            "subjects__class_subject__instructor__user",
            "subjects__grade",
            "subjects__attendance_records",
        )
        .order_by("-semester__academic_year__start_date", "-semester__term")
        if student
        else Enrollment.objects.none()
    )
    return render(
        request,
        "students/student_dashboard.html",
        {"student": student, "subjects": subjects, "enrollments": enrollments},
    )


@role_required(UserProfile.Role.REGISTRAR)
def student_list(request):
    query = request.GET.get("q", "").strip()
    show_archived = request.GET.get("archived") == "1"
    students = Student.objects.select_related("course", "user").filter(
        is_archived=show_archived
    )
    if query:
        students = students.filter(
            Q(student_id__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(course__name__icontains=query)
            | Q(course__code__icontains=query)
        )

    page = Paginator(students, 25).get_page(request.GET.get("page"))
    context = {
        "students": page,
        "page_obj": page,
        "query": query,
        "show_archived": show_archived,
        "student_count": students.count(),
        "course_count": Course.objects.count(),
    }
    return render(request, "students/student_list.html", context)


@role_required(UserProfile.Role.REGISTRAR)
def student_create(request):
    if request.method == "POST":
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save()
            record_activity(
                actor=request.user,
                action=AuditLog.Action.CREATE,
                entity=student,
                description=f"Student record {student.student_id} created.",
                request=request,
            )
            messages.success(request, f"{student.full_name} was added successfully.")
            return redirect("students:list")
    else:
        form = StudentForm()
    return render(
        request,
        "students/student_form.html",
        {"form": form, "page_title": "Add student"},
    )


@role_required(UserProfile.Role.REGISTRAR)
def student_update(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == "POST":
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            student = form.save()
            record_activity(
                actor=request.user,
                action=AuditLog.Action.UPDATE,
                entity=student,
                description=f"Student record {student.student_id} updated.",
                request=request,
            )
            messages.success(request, f"{student.full_name}'s record was updated.")
            return redirect("students:list")
    else:
        form = StudentForm(instance=student)
    return render(
        request,
        "students/student_form.html",
        {"form": form, "page_title": "Edit student", "student": student},
    )


@role_required(UserProfile.Role.REGISTRAR)
def student_delete(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == "POST":
        student.is_archived = request.POST.get("action") != "restore"
        student.save(update_fields=["is_archived", "updated_at"])
        action = AuditLog.Action.UPDATE
        verb = "archived" if student.is_archived else "restored"
        record_activity(
            actor=request.user,
            action=action,
            entity=student,
            description=f"Student record {student.student_id} {verb}.",
            request=request,
        )
        messages.success(request, f"{student.full_name}'s record was {verb}.")
        return redirect("students:list")
    return render(request, "students/student_confirm_delete.html", {"student": student})


@role_required(UserProfile.Role.REGISTRAR)
def course_list(request):
    courses = Course.objects.annotate(
        student_count=Count("students", distinct=True),
        subject_count=Count("subjects", distinct=True),
    )
    return render(request, "students/course_list.html", {"courses": courses})


@role_required(UserProfile.Role.REGISTRAR)
def course_create(request):
    if request.method == "POST":
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save()
            messages.success(request, f"{course.name} was added to the course catalog.")
            return redirect("students:courses")
    else:
        form = CourseForm()
    return render(
        request,
        "students/catalog_form.html",
        {"form": form, "page_title": "Add course"},
    )


@role_required(UserProfile.Role.REGISTRAR)
def subject_list(request):
    subjects = Subject.objects.select_related("course").prefetch_related("instructors")
    return render(request, "students/subject_list.html", {"subjects": subjects})


@role_required(UserProfile.Role.REGISTRAR)
def subject_create(request):
    if request.method == "POST":
        form = SubjectForm(request.POST)
        if form.is_valid():
            subject = form.save()
            messages.success(request, f"{subject.name} was added to the subject catalog.")
            return redirect("students:subjects")
    else:
        form = SubjectForm()
    return render(
        request,
        "students/catalog_form.html",
        {"form": form, "page_title": "Add subject"},
    )
