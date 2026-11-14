from django.urls import path

from . import views

app_name = "enrollment"

urlpatterns = [
    path("student/enroll/", views.student_enrollment_request, name="student_request"),
    path("registrar/enrollments/", views.enrollment_list, name="list"),
    path("registrar/enrollments/add/", views.enrollment_create, name="create"),
    path(
        "registrar/enrollments/<int:pk>/decide/",
        views.decide_enrollment,
        name="decide",
    ),
]
