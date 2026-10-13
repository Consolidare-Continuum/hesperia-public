from django.urls import path

from . import views

urlpatterns = [
    path("", views.operator_home, name="operator_home"),
    path("sessions/", views.sessions_index, name="sessions_index"),
    path("inspector/<str:session_id>/export.json", views.export_segment_json, name="inspector_export_segment"),
    path("inspector/<str:session_id>/openai-proxy/", views.openai_proxy, name="inspector_openai_proxy"),
    path("inspector/<str:session_id>/", views.session_inspector, name="session_inspector"),
    path("health/", views.health, name="health"),
    path("preview/client/", views.client_preview, name="client_preview"),
    path("preview/artifacts/", views.artifact_sample, name="artifact_sample"),
]
