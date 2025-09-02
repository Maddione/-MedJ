from django.http import JsonResponse
from django.urls import path, reverse_lazy
from django.views.generic import TemplateView
from django.contrib.auth.views import LogoutView, PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView, PasswordChangeView, PasswordChangeDoneView
from django.contrib.auth.decorators import login_required

from .views.auth import RememberLoginView
from .views.upload import upload_page, upload_preview, upload_confirm, upload_history
from .views.exports import print_csv, print_pdf
from .views.share import create_download_links, share_document_page, create_share_token, share_view, share_qr, share_revoke, qr_for_url

app_name = "medj"

def events_by_specialty_stub(request):
    return JsonResponse({"events": []})

def tags_autocomplete_stub(request):
    q = (request.GET.get("q") or "").strip()
    return JsonResponse({"results": []})

urlpatterns = [
    path("ajax/events/by-specialty/", events_by_specialty_stub, name="events_by_specialty"),
    path("ajax/tags/autocomplete/", tags_autocomplete_stub, name="tags_autocomplete"),

    path("", TemplateView.as_view(template_name="basetemplates/landingpage.html"), name="landingpage"),

    path("login/", RememberLoginView.as_view(template_name="auth/login.html"), name="login"),
    path("logout/", LogoutView.as_view(next_page="/login/"), name="logout"),
    path("register/", TemplateView.as_view(template_name="auth/register.html"), name="register"),

    path("password-reset/", PasswordResetView.as_view(
        template_name="password/reset_form.html",
        email_template_name="password/reset_email.txt",
        subject_template_name="password/reset_subject.txt",
        success_url=reverse_lazy("medj:password_reset_done")
    ), name="password_reset"),
    path("password-reset/done/", PasswordResetDoneView.as_view(
        template_name="password/reset_done.html"
    ), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", PasswordResetConfirmView.as_view(
        template_name="password/reset_confirm.html",
        success_url=reverse_lazy("medj:password_reset_complete")
    ), name="password_reset_confirm"),
    path("reset/done/", PasswordResetCompleteView.as_view(
        template_name="password/reset_complete.html"
    ), name="password_reset_complete"),

    path("share/", login_required(share_document_page), name="share"),
    path("share/document/", login_required(share_document_page), name="share_document_page"),
    path("share/document/<int:medical_event_id>/", login_required(share_document_page), name="share_document_page"),

    path("dashboard/", login_required(TemplateView.as_view(template_name="main/dashboard.html")), name="dashboard"),
    path("casefiles/", login_required(TemplateView.as_view(template_name="main/casefiles.html")), name="casefiles"),
    path("personal-card/", login_required(TemplateView.as_view(template_name="main/personalcard.html")), name="personal_card"),
    path("personalcard/", login_required(TemplateView.as_view(template_name="main/personalcard.html")), name="personalcard"),
    path("history/", login_required(TemplateView.as_view(template_name="main/history.html")), name="history"),

    path("upload/", login_required(upload_page), name="upload"),
    path("upload/preview/", login_required(upload_preview), name="upload_preview"),
    path("upload/confirm/", login_required(upload_confirm), name="upload_confirm"),
    path("uploads/history/", login_required(upload_history), name="upload_history"),

    path("documents/", login_required(TemplateView.as_view(template_name="subpages/upload_history.html")), name="documents"),
    path("documents/<int:pk>/", login_required(TemplateView.as_view(template_name="subpages/document_detail.html")), name="document_detail"),
    path("documents/<int:pk>/edit/", login_required(TemplateView.as_view(template_name="subpages/document_edit.html")), name="document_edit"),
    path("documents/<int:pk>/edit-tags/", login_required(TemplateView.as_view(template_name="subpages/document_edit_tags.html")), name="document_edit_tags"),
    path("documents/<int:pk>/move/", login_required(TemplateView.as_view(template_name="subpages/document_move.html")), name="document_move"),
    path("documents/<int:pk>/export/pdf/", login_required(TemplateView.as_view(template_name="subpages/document_export_pdf.html")), name="document_export_pdf"),

    path("events/history/", login_required(TemplateView.as_view(template_name="subpages/event_history.html")), name="event_history"),
    path("events/<int:pk>/", login_required(TemplateView.as_view(template_name="subpages/event_detail.html")), name="medical_event_detail"),
    path("events/<int:pk>/export/pdf/", login_required(TemplateView.as_view(template_name="subpages/event_export_pdf.html")), name="event_export_pdf"),

    path("labtests/", login_required(TemplateView.as_view(template_name="subpages/labtests.html")), name="labtests"),
    path("labtests/<int:pk>/edit/", login_required(TemplateView.as_view(template_name="subpages/labtest_edit.html")), name="labtest_edit"),
    path("labtests/csv/print/", login_required(TemplateView.as_view(template_name="subpages/csv_print.html")), name="csv_print"),

    path("s/<uuid:token>/", share_view, name="share_view"),
    path("s/<uuid:token>/qr.png", share_qr, name="share_qr"),
    path("share/revoke/<uuid:token>/", login_required(share_revoke), name="share_revoke"),
    path("share/create-links/", login_required(create_download_links), name="create_download_links"),
    path("share/tokens/create/", login_required(create_share_token), name="create_share_token"),
    path("share/qr-for-url.png", qr_for_url, name="qr_for_url"),

    path("_tpl/auth/login/", TemplateView.as_view(template_name="auth/login.html"), name="tpl_auth_login"),
    path("_tpl/auth/register/", TemplateView.as_view(template_name="auth/register.html"), name="tpl_auth_register"),
    path("_tpl/base.html", TemplateView.as_view(template_name="basetemplates/base.html"), name="tpl_base"),
    path("_tpl/base_app.html", TemplateView.as_view(template_name="basetemplates/base_app.html"), name="tpl_base_app"),
    path("_tpl/base_public.html", TemplateView.as_view(template_name="basetemplates/base_public.html"), name="tpl_base_public"),
    path("_tpl/landingpage.html", TemplateView.as_view(template_name="basetemplates/landingpage.html"), name="tpl_landingpage"),
    path("_tpl/main/casefiles.html", TemplateView.as_view(template_name="main/casefiles.html"), name="tpl_main_casefiles"),
    path("_tpl/main/dashboard.html", TemplateView.as_view(template_name="main/dashboard.html"), name="tpl_main_dashboard"),
    path("_tpl/main/history.html", TemplateView.as_view(template_name="main/history.html"), name="tpl_main_history"),
    path("_tpl/main/personalcard.html", TemplateView.as_view(template_name="main/personalcard.html"), name="tpl_main_personalcard"),
    path("_tpl/main/share.html", TemplateView.as_view(template_name="main/share.html"), name="tpl_main_share"),
    path("_tpl/main/upload.html", TemplateView.as_view(template_name="main/upload.html"), name="tpl_main_upload"),
    path("_tpl/subpages/csv_print.html", TemplateView.as_view(template_name="subpages/csv_print.html"), name="tpl_sub_csv_print"),
    path("_tpl/subpages/doctors.html", TemplateView.as_view(template_name="subpages/doctors.html"), name="tpl_sub_doctors"),
    path("_tpl/subpages/document_detail.html", TemplateView.as_view(template_name="subpages/document_detail.html"), name="tpl_sub_document_detail"),
    path("_tpl/subpages/document_edit.html", TemplateView.as_view(template_name="subpages/document_edit.html"), name="tpl_sub_document_edit"),
    path("_tpl/subpages/document_edit_tags.html", TemplateView.as_view(template_name="subpages/document_edit_tags.html"), name="tpl_sub_document_edit_tags"),
    path("_tpl/subpages/document_export_pdf.html", TemplateView.as_view(template_name="subpages/document_export_pdf.html"), name="tpl_sub_document_export_pdf"),
    path("_tpl/subpages/document_move.html", TemplateView.as_view(template_name="subpages/document_move.html"), name="tpl_sub_document_move"),
    path("_tpl/subpages/event_detail.html", TemplateView.as_view(template_name="subpages/event_detail.html"), name="tpl_sub_event_detail"),
    path("_tpl/subpages/event_edit_tags.html", TemplateView.as_view(template_name="subpages/event_edit_tags.html"), name="tpl_sub_event_edit_tags"),
    path("_tpl/subpages/event_export_pdf.html", TemplateView.as_view(template_name="subpages/event_export_pdf.html"), name="tpl_sub_event_export_pdf"),
    path("_tpl/subpages/event_history.html", TemplateView.as_view(template_name="subpages/event_history.html"), name="tpl_sub_event_history"),
    path("_tpl/subpages/labtest_edit.html", TemplateView.as_view(template_name="subpages/labtest_edit.html"), name="tpl_sub_labtest_edit"),
    path("_tpl/subpages/labtests.html", TemplateView.as_view(template_name="subpages/labtests.html"), name="tpl_sub_labtests"),
    path("_tpl/subpages/medical_event_confirm_delete.html", TemplateView.as_view(template_name="subpages/medical_event_confirm_delete.html"), name="tpl_sub_medical_event_confirm_delete"),
    path("_tpl/subpages/medical_event_form.html", TemplateView.as_view(template_name="subpages/medical_event_form.html"), name="tpl_sub_medical_event_form"),
    path("_tpl/main/profile.html", TemplateView.as_view(template_name="main/profile.html"), name="tpl_sub_profile"),

    path("print/csv/", login_required(print_csv), name="print_csv"),
    path("print/pdf/", login_required(print_pdf), name="print_pdf"),

    path("profile/", login_required(TemplateView.as_view(template_name="main/profile.html")), name="profile"),

    path("password-change/", login_required(PasswordChangeView.as_view(
        template_name="password/change_form.html",
        success_url=reverse_lazy("medj:password_change_done")
    )), name="password_change"),
    path("password-change/done/", login_required(PasswordChangeDoneView.as_view(
        template_name="password/change_done.html"
    )), name="password_change_done"),
]
