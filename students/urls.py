from django.urls import path

from . import views

app_name = "students"

urlpatterns = [
    path("", views.role_home, name="home"),
    path("register/", views.student_register, name="student_register"),
    path("registrar/", views.registrar_dashboard, name="registrar_dashboard"),
    path("registrar/reports/", views.registrar_reports, name="reports"),
    path(
        "registrar/reports/<str:report_type>.csv",
        views.registrar_report_export,
        name="report_export",
    ),
    path(
        "registrar/accounts/add/",
        views.staff_account_create,
        name="staff_account_create",
    ),
    path("registrar/students/", views.student_list, name="list"),
    path("registrar/students/add/", views.student_create, name="create"),
    path("registrar/students/<int:pk>/edit/", views.student_update, name="update"),
    path("registrar/students/<int:pk>/delete/", views.student_delete, name="delete"),
    path("registrar/courses/", views.course_list, name="courses"),
    path("registrar/courses/add/", views.course_create, name="course_create"),
    path("registrar/subjects/", views.subject_list, name="subjects"),
    path("registrar/subjects/add/", views.subject_create, name="subject_create"),
    path("instructor/", views.instructor_dashboard, name="instructor_dashboard"),
    path(
        "instructor/subjects/<int:pk>/",
        views.instructor_subject,
        name="instructor_subject",
    ),
    path("student/", views.student_dashboard, name="student_dashboard"),
]
