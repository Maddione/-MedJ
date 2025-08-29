from django.urls import path
from . import views

app_name = "medj"

urlpatterns = [
    path("", views.landing_view, name="landing"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.register, name="register"),

    path("dashboard/", views.event_list, name="dashboard"),
    path("upload/", views.upload_document, name="upload"),
    path("upload-history/", views.upload_history, name="upload_history"),
    path("share/new/", views.share_page_view, name="share"),
    path("casefiles/", views.casefiles_view, name="casefiles"),
    path("profile/", views.profile_view, name="profile"),
    path("doctors/", views.practitioners_list, name="doctors"),

    path("labtests/", views.labtests_overview, name="labtests"),
    path("labtests/<int:pk>/edit/", views.labtest_edit, name="labtest_edit"),

    path("documents/<int:pk>/", views.document_detail, name="document_detail"),
    path("documents/<int:pk>/edit/", views.document_edit, name="document_edit"),
    path("documents/<int:pk>/edit-tags/", views.document_edit_tags, name="document_edit_tags"),
    path("documents/<int:pk>/move/", views.document_move, name="document_move"),
    path("documents/<int:pk>/export-pdf/", views.generate_pdf, name="document_export_pdf"),

    path("events/history/", views.event_list, name="medical_event_list"),
    path("events/new/", views.event_new, name="event_new"),
    path("events/<int:pk>/", views.event_detail, name="medical_event_detail"),
    path("events/<int:pk>/edit-tags/", views.event_edit_tags, name="event_edit_tags"),
    path("events/<int:pk>/export-pdf/", views.export_event_pdf, name="event_export_pdf"),
    path("events/<int:pk>/delete/", views.medical_event_delete, name="event_delete"),

    path("share/<uuid:token>/", views.share_view, name="share_view"),
    path("share/<uuid:token>/qr/", views.share_qr, name="share_qr"),
    path("share/<uuid:token>/revoke/", views.share_revoke, name="share_revoke"),

    path("ajax/events-by-specialty/", views.events_by_specialty, name="events_by_specialty"),
    path("ajax/tags-autocomplete/", views.tags_autocomplete, name="tags_autocomplete"),
]