from django.urls import path

from . import views

app_name = "grading"

urlpatterns = [
    path("classes/<int:pk>/grades/", views.grade_roster, name="roster"),
    path("enrollment-subjects/<int:pk>/grade/", views.grade_update, name="update"),
]
