from django.urls import path

from . import views

urlpatterns = [
    path("upload", views.upload),
    path("conversas", views.conversas),
    path("conversas/analisar", views.analisar),
    path("conversas/<int:conversa_id>", views.conversa),
    path("metricas", views.metricas),
    path("register", views.create),
    path("login", views.login),
    path("openapi.yaml", views.openapi_spec, name="openapi_spec"),
    path("docs", views.docs, name="docs"),
]
