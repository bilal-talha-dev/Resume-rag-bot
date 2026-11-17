from django.urls import path, re_path
from rag_app import views

urlpatterns = [
    # status & config
    path("api/health", views.health_view),
    path("api/config", views.config_view),
    # ingestion pipeline
    path("api/ingest", views.ingest_view),
    path("api/ingest/status", views.ingest_status_view),
    path("api/upload", views.upload_view),
    path("api/candidates", views.candidates_view),
    path("api/candidates/<path:source>", views.candidate_detail_view),
    # retrieval pipeline
    path("api/query", views.query_view),
    path("api/chunks", views.chunks_view),
    # legacy
    path("api/reingest", views.reingest_view),
    re_path(r"^(?!api/).*$", views.spa_index_view, name="spa_index"),
]
