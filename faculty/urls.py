from django.urls import path

from . import views

app_name = "faculty"

urlpatterns = [path("classes/", views.class_list, name="classes")]
