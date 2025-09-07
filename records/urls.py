from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    LogoutView,
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
    PasswordChangeView,
    PasswordChangeDoneView,
)
from django.urls import path, reverse_lazy
from django.views.generic import TemplateView

from .views.auth import RememberLoginView, RegisterView
from .views.dashboard import dashboard
from .views.casefiles import casefiles
from .views.documents import document_detail
from .views.events import event_detail
from .views.doctors_views import doctors_list
from .views.labs import labtests
from .views.share import share_document_page
from .views.personalcard import (
    PersonalCardView,
    public_personalcard,
    personalcard_share_enable_api,
    personalcard_qr,
)
from .views.profile import SettingsView
from .views.upload import upload
from .views.pages import history_view
from .views.api_upload import (
    upload_ocr as api_upload_ocr,
    upload_analyze as api_upload_analyze,
    upload_confirm as api_upload_confirm,
    events_suggest,
)
from .views.doctors_api import doctors_suggest
from .views.share_api import (
    share_create,
    share_history as share_history_api,
    share_revoke,
    share_public,
    share_qr_png
)

app_name = "medj"

urlpatterns = [
    path("", TemplateView.as_view(template_name="main/landingpage.html"), name="landingpage"),

    path("auth/login/", RememberLoginView.as_view(), name="login"),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/logout/", LogoutView.as_view(next_page=reverse_lazy("medj:landingpage")), name="logout"),

    path("password/change/", login_required(PasswordChangeView.as_view(
        template_name="password/change_form.html",
        success_url=reverse_lazy("medj:password_change_done")
    )), name="password_change"),
    path("password/change/done/", login_required(PasswordChangeDoneView.as_view(
        template_name="password/change_done.html"
    )), name="password_change_done"),

    path("password/reset/", PasswordResetView.as_view(
        template_name="password/password_reset_form.html",
        email_template_name="password/password_reset_email.txt",
        subject_template_name="password/password_reset_subject.txt",
        success_url=reverse_lazy("medj:password_reset_done")
    ), name="password_reset"),
    path("password/reset/done/", PasswordResetDoneView.as_view(
        template_name="password/password_reset_done.html"
    ), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", PasswordResetConfirmView.as_view(
        template_name="password/password_reset_confirm.html",
        success_url=reverse_lazy("medj:password_reset_complete")
    ), name="password_reset_confirm"),
    path("reset/done/", PasswordResetCompleteView.as_view(
        template_name="password/password_reset_complete.html"
    ), name="password_reset_complete"),

    path("dashboard/", login_required(dashboard), name="dashboard"),
    path("upload/", login_required(upload), name="upload"),
    path("history/", login_required(history_view), name="history"),
    path("casefiles/", login_required(casefiles), name="casefiles"),
    path("personalcard/", login_required(PersonalCardView.as_view()), name="personalcard"),
    path("profile/", login_required(SettingsView.as_view()), name="profile"),
    path("doctors/", login_required(doctors_list), name="doctors"),
    path("labtests/", login_required(labtests), name="labtests"),
    path("share/", login_required(share_document_page), name="share"),
    path("share/history/", login_required(TemplateView.as_view(template_name="subpages/share_history.html")), name="share_history_page"),

    path("documents/<int:pk>/", login_required(document_detail), name="document_detail"),
    path("events/<int:pk>/", login_required(event_detail), name="event_detail"),

    path("s/<str:token>/", share_public, name="share_public"),
    path("personalcard/public/<str:token>/", public_personalcard, name="public_personalcard"),

    path("api/upload/ocr/", login_required(api_upload_ocr), name="upload_ocr"),
    path("api/upload/analyze/", login_required(api_upload_analyze), name="upload_analyze"),
    path("api/upload/confirm/", login_required(api_upload_confirm), name="upload_confirm"),
    path("api/events/suggest/", login_required(events_suggest), name="events_suggest"),
    path("api/doctors/suggest/", login_required(doctors_suggest), name="doctors_suggest"),

    path("api/share/create/", login_required(share_create), name="share_create"),
    path("api/share/history/", login_required(share_history_api), name="share_history_api"),
    path("api/share/revoke/<str:token>/", login_required(share_revoke), name="share_revoke"),
    path("api/share/qr/<str:token>.png", login_required(share_qr_png), name="share_qr"),

    path("api/personalcard/share/enable/", login_required(personalcard_share_enable_api), name="personalcard_share_enable_api"),
    path("api/personalcard/qr/<str:token>/", login_required(personalcard_qr), name="personalcard_qr"),
]