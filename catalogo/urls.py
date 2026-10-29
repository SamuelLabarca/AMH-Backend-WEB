from django.urls import path

from . import views

urlpatterns = [
    path("catalogo", views.Catalogo.as_view()),
]
