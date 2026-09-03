from django.urls import path

from . import views

urlpatterns = [
    path("upload", views.upload),
    path("conversas", views.conversas),
    path("conversas/<int:conversa_id>", views.conversa),
    path("metricas", views.metricas),
]
