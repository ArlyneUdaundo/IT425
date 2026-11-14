from django.urls import path

from . import views

app_name = "attendance"

urlpatterns = [
    path("classes/<int:pk>/attendance/", views.mark_attendance, name="mark"),
]
