from django.urls import path, reverse_lazy
from django.views.generic import TemplateView
from django.contrib.auth.views import (
    LogoutView, PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView,
    PasswordChangeView, PasswordChangeDoneView
)
from django.contrib.auth.decorators import login_required

from .views.auth import RememberLoginView, RegisterView
from .views.settings import SettingsView
from .views.personalcard import PersonalCardView
from .views.upload import upload_page, upload_preview, upload_confirm, upload_history
from .views.exports import document_export_pdf, event_export_pdf, print_csv, print_pdf
from .views.share import (
    create_download_links, share_document_page, create_share_token,
    share_view, share_qr, share_revoke, qr_for_url
)
from .views.share_csv import csv_print_page, csv_print_to_pdf
from .views.labs import labtests, labtests_view, labtest_edit, export_lab_csv
from .views.events import events_by_specialty, tags_autocomplete
from records.views.personalcard import PersonalCardView, personalcard_qr, public_personalcard, enable_share

app_name = "medj"

urlpatterns = [
    path("ajax/events/by-specialty/", events_by_specialty, name="events_by_specialty"),
    path("ajax/tags/autocomplete/", tags_autocomplete, name="tags_autocomplete"),

    path("", TemplateView.as_view(template_name="basetemplates/landingpage.html"), name="landingpage"),

    path("login/", RememberLoginView.as_view(template_name="auth/login.html"), name="login"),
    path("logout/", LogoutView.as_view(next_page="/login/"), name="logout"),
    path("register/", RegisterView.as_view(), name="register"),

    path("password-reset/", PasswordResetView.as_view(
        template_name="password/password_reset_form.html",
        email_template_name="password/password_reset_email.txt",
        subject_template_name="password/password_reset_subject.txt",
        success_url=reverse_lazy("medj:password_reset_done")
    ), name="password_reset"),
    path("password-reset/done/", PasswordResetDoneView.as_view(
        template_name="password/password_reset_done.html"
    ), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", PasswordResetConfirmView.as_view(
        template_name="password/password_reset_confirm.html",
        success_url=reverse_lazy("medj:password_reset_complete")
    ), name="password_reset_confirm"),
    path("reset/done/", PasswordResetCompleteView.as_view(
        template_name="password/password_reset_complete.html"
    ), name="password_reset_complete"),

    path("password-change/", login_required(PasswordChangeView.as_view(
        template_name="password/change_form.html",
        success_url=reverse_lazy("medj:password_change_done")
    )), name="password_change"),
    path("password-change/done/", login_required(PasswordChangeDoneView.as_view(
        template_name="password/change_done.html"
    )), name="password_change_done"),

    path("share/", login_required(share_document_page), name="share"),
    path("share/document/", login_required(share_document_page), name="share_document_page"),
    path("share/document/<int:medical_event_id>/", login_required(share_document_page), name="share_document_page"),

    path("dashboard/", login_required(TemplateView.as_view(template_name="main/dashboard.html")), name="dashboard"),
    path("casefiles/", login_required(TemplateView.as_view(template_name="main/casefiles.html")), name="casefiles"),
    path("profile/", login_required(SettingsView.as_view(template_name="main/personalcard.html")), name="profile"),
    path("personalcard/", login_required(PersonalCardView.as_view()), name="personalcard"),
    path("personalcard/share/enable/", enable_share, name="personalcard_share_enable"),
    path("personalcard/qr/<str:token>.png", personalcard_qr, name="personalcard_qr"),
    path("p/<str:token>/", public_personalcard, name="personalcard_public"),
    path("personal-card/", login_required(PersonalCardView.as_view()), name="personal_card"),
    path("history/", login_required(TemplateView.as_view(template_name="main/history.html")), name="history"),

    path("upload/", login_required(upload_page), name="upload"),
    path("upload/page/", login_required(TemplateView.as_view(template_name="main/upload.html")), name="upload_page"),
    path("upload/preview/", login_required(upload_preview), name="upload_preview"),
    path("upload/confirm/", login_required(upload_confirm), name="upload_confirm"),
    path("uploads/history/", login_required(upload_history), name="upload_history"),

    path("documents/", login_required(TemplateView.as_view(template_name="subpages/upload_history.html")), name="documents"),
    path("documents/<int:pk>/", login_required(TemplateView.as_view(template_name="subpages/document_detail.html")), name="document_detail"),
    path("documents/<int:pk>/edit/", login_required(TemplateView.as_view(template_name="subpages/document_edit.html")), name="document_edit"),
    path("documents/<int:pk>/edit-tags/", login_required(TemplateView.as_view(template_name="subpages/document_edit_tags.html")), name="document_edit_tags"),
    path("documents/<int:pk>/move/", login_required(TemplateView.as_view(template_name="subpages/document_move.html")), name="document_move"),
    path("documents/<int:pk>/export/pdf/", login_required(document_export_pdf), name="document_export_pdf"),

    path("events/history/", login_required(TemplateView.as_view(template_name="subpages/event_history.html")), name="event_history"),
    path("events/list/", login_required(TemplateView.as_view(template_name="subpages/event_history.html")), name="medical_event_list"),
    path("events/detail/<int:pk>/", login_required(TemplateView.as_view(template_name="subpages/event_detail.html")), name="event_detail"),
    path("events/<int:pk>/export/pdf/", login_required(event_export_pdf), name="event_export_pdf"),
    path("events/<int:pk>/delete/", login_required(TemplateView.as_view(template_name="subpages/medical_event_confirm_delete.html")), name="medical_event_delete"),

    path("labtests/", login_required(labtests), name="labtests"),
    path("labtests/<int:event_id>/", login_required(labtests_view), name="labtests_view"),
    path("labtests/<int:event_id>/edit/", login_required(labtest_edit), name="labtest_edit"),
    path("labtests/export/csv/", login_required(export_lab_csv), name="export_lab_csv"),
    path("labs/export/csv/print/", login_required(csv_print_page), name="csv_print_page"),
    path("labs/export/csv/print.pdf", login_required(csv_print_to_pdf), name="csv_print_to_pdf"),

    path("s/<uuid:token>/", share_view, name="share_view"),
    path("s/<uuid:token>/qr.png", share_qr, name="share_qr"),
    path("share/revoke/<uuid:token>/", login_required(share_revoke), name="share_revoke"),
    path("share/create-links/", login_required(create_download_links), name="create_download_links"),
    path("share/tokens/create/", login_required(create_share_token), name="create_share_token"),

    path("print/csv/", login_required(print_csv), name="print_csv"),
    path("print/pdf/", login_required(print_pdf), name="print_pdf"),

    path("doctors/", login_required(TemplateView.as_view(template_name="subpages/doctors.html")), name="doctors"),
]
