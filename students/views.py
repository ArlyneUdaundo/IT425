from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CourseForm, StudentForm, SubjectForm
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


@role_required(UserProfile.Role.REGISTRAR)
def registrar_dashboard(request):
    context = {
        "student_count": Student.objects.count(),
        "course_count": Course.objects.count(),
        "subject_count": Subject.objects.count(),
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
    }
    return render(request, "students/registrar_dashboard.html", context)


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
        Subject.objects.filter(course=student.course).prefetch_related("instructors")
        if student
        else Subject.objects.none()
    )
    return render(
        request,
        "students/student_dashboard.html",
        {"student": student, "subjects": subjects},
    )


@role_required(UserProfile.Role.REGISTRAR)
def student_list(request):
    query = request.GET.get("q", "").strip()
    students = Student.objects.select_related("course", "user").all()
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
        "student_count": Student.objects.count(),
        "course_count": Course.objects.count(),
    }
    return render(request, "students/student_list.html", context)


@role_required(UserProfile.Role.REGISTRAR)
def student_create(request):
    if request.method == "POST":
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save()
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
        name = student.full_name
        student.delete()
        messages.success(request, f"{name}'s record was deleted.")
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
