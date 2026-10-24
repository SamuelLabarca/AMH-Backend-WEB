from django.urls import path

from . import views

urlpatterns = [
    path("cuenta", views.Cuenta.as_view()),
]
