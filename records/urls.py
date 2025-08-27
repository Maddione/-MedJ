from django.urls import path
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views
from . import views

app_name = "medj"

urlpatterns = [
    path("", TemplateView.as_view(template_name="basetemplates/landingpage.html"), name="landing"),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="medj:landing"), name="logout"),
    path("register/", views.register, name="register"),
    path("dashboard/", TemplateView.as_view(template_name="main/dashboard.html"), name="dashboard"),
    path("upload/", TemplateView.as_view(template_name="main/upload.html"), name="upload"),
    path("history/", TemplateView.as_view(template_name="main/history.html"), name="history"),
    path("share/", TemplateView.as_view(template_name="main/share.html"), name="share"),
    path("casefiles/", TemplateView.as_view(template_name="main/casefiles.html"), name="casefiles"),
    path("profile/", TemplateView.as_view(template_name="subpages/profile.html"), name="profile"),
    path("doctors/", TemplateView.as_view(template_name="subpages/doctors.html"), name="doctors"),
    path("labtests/", TemplateView.as_view(template_name="subpages/labtests.html"), name="labtests"),
    path("upload-history/", TemplateView.as_view(template_name="subpages/upload_history.html"), name="upload_history"),
    path("documents/<int:pk>/", TemplateView.as_view(template_name="subpages/document_detail.html"), name="document_detail"),
    path("documents/<int:pk>/edit/", TemplateView.as_view(template_name="subpages/document_edit.html"), name="document_edit"),
    path("documents/<int:pk>/edit-tags/", TemplateView.as_view(template_name="subpages/document_edit_tags.html"), name="document_edit_tags"),
    path("documents/<int:pk>/move/", TemplateView.as_view(template_name="subpages/document_move.html"), name="document_move"),
    path("documents/<int:pk>/export-pdf/", TemplateView.as_view(template_name="subpages/document_export_pdf.html"), name="document_export_pdf"),
    path("events/<int:pk>/", TemplateView.as_view(template_name="subpages/event_detail.html"), name="event_detail"),
    path("events/<int:pk>/edit-tags/", TemplateView.as_view(template_name="subpages/event_edit_tags.html"), name="event_edit_tags"),
    path("events/<int:pk>/export-pdf/", TemplateView.as_view(template_name="subpages/event_export_pdf.html"), name="event_export_pdf"),
    path("events/<int:pk>/history/", TemplateView.as_view(template_name="subpages/event_history.html"), name="event_history"),
    path("events/<int:pk>/delete/", TemplateView.as_view(template_name="subpages/medical_event_confirm_delete.html"), name="event_delete"),
    path("events/new/", TemplateView.as_view(template_name="subpages/medical_event_form.html"), name="event_new"),
    path("labtests/<int:pk>/edit/", TemplateView.as_view(template_name="subpages/labtest_edit.html"), name="labtest_edit"),
    path("share/<uuid:token>/", TemplateView.as_view(template_name="subpages/share_view.html"), name="share_view"),
]
