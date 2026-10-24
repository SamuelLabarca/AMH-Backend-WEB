from django.urls import path

from . import views

urlpatterns = [
    path("pagos", views.Pagos.as_view()),
]
