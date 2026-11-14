from django.urls import path

from . import views

app_name = "admissions"

urlpatterns = [
    path("apply/", views.apply, name="apply"),
    path("registrar/admissions/", views.application_list, name="list"),
    path(
        "registrar/admissions/<int:pk>/review/",
        views.review_application,
        name="review",
    ),
]
