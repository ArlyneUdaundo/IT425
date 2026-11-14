from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("", include("admissions.urls")),
    path("", include("enrollment.urls")),
    path("", include("grading.urls")),
    path("", include("attendance.urls")),
    path("", include("faculty.urls")),
    path("", include("students.urls")),
]
