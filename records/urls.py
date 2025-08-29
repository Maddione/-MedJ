from django.urls import path, re_path
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView
from . import views

app_name = "medj"

urlpatterns = [
    path("", TemplateView.as_view(template_name="basetemplates/landingpage.html"), name="landing"),
    path("register/", views.register, name="register"),
    path("login/", views.custom_login_view, name="login"),
    path("logout/", views.custom_logout_view, name="logout"),

    re_path(r"^share/(?P<token>[0-9a-fA-F-]{36})/$", views.share_view, name="share_view"),
    re_path(r"^share/(?P<token>[0-9a-fA-F-]{36})/qr/$", views.share_qr, name="share_qr"),
    re_path(r"^share/(?P<token>[0-9a-fA-F-]{36})/revoke/$", views.share_revoke, name="share_revoke"),  # POST + login_required в самото view

    path("dashboard/", views.dashboard, name="dashboard"),
    path("upload/", views.upload_document, name="upload_page"),
    path("uploads/history/", views.upload_history, name="upload_history"),

    path("ajax/events-by-specialty/", views.events_by_specialty, name="events_by_specialty"),
    path("ajax/tags/", views.tags_autocomplete, name="tags_autocomplete"),

    path("events/", views.event_list, name="medical_event_list"),
    path("events/<int:pk>/", views.event_detail, name="medical_event_detail"),
    path("events/<int:pk>/delete/", views.medical_event_delete, name="medical_event_delete"),
    path("events/<int:pk>/tags/", views.event_edit_tags, name="event_edit_tags"),
    path("events/<int:pk>/export/pdf/", views.export_event_pdf, name="export_event_pdf"),
    path("events/<int:pk>/export/csv/", views.export_lab_csv, name="export_lab_csv"),

    path("documents/<int:pk>/", views.document_detail, name="document_detail"),
    path("documents/<int:pk>/edit/", views.document_edit, name="document_edit"),
    path("documents/<int:pk>/tags/", views.document_edit_tags, name="document_edit_tags"),
    path("documents/<int:pk>/move/", views.document_move, name="document_move"),

    path("labtests/", views.labtests_view, name="labtests"),
    path("labtests/<int:pk>/edit/", views.labtest_edit, name="labtest_edit"),

    path("doctors/", views.practitioners_list, name="practitioners_list"),
]
