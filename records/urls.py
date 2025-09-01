from django.http import JsonResponse
from django.urls import path, re_path
from django.views.generic import TemplateView
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponse, HttpResponseNotAllowed, HttpResponseRedirect
from django.urls import reverse
from .forms import LoginForm
from .views.upload import upload_page, upload_preview, upload_confirm, upload_history

import base64

# ---------- AJAX stubs ----------
def events_by_specialty_stub(request):

    return JsonResponse({
        "events": []
    })

def tags_autocomplete_stub(request):

    q = (request.GET.get("q") or "").strip()
    return JsonResponse({
        "results": []
    })


app_name = "medj"

# ---- STUB handlers (временно, докато вържем реалните share/views) ----
def share_create_stub(request):
    if request.method == "POST":
        return HttpResponseRedirect(reverse("medj:share"))
    return HttpResponseNotAllowed(["POST"])

def share_qr_stub(request, token):
    # 1x1 transparent PNG
    png_base64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGNgYAAAAAMA"
        "ASsJTYQAAAAASUVORK5CYII="
    )
    return HttpResponse(base64.b64decode(png_base64), content_type="image/png")

urlpatterns = [

    path("ajax/events/by-specialty/", events_by_specialty_stub, name="events_by_specialty"),
    path("ajax/tags/autocomplete/", tags_autocomplete_stub, name="tags_autocomplete"),
    # ---------- Публични ----------
    path("", TemplateView.as_view(
        template_name="basetemplates/landingpage.html"), name="landingpage"),
    path("login/", LoginView.as_view(
        template_name="auth/login.html",
        authentication_form=LoginForm,
        redirect_authenticated_user=True), name="login"),
    path("logout/", LogoutView.as_view(next_page="/"), name="logout"),
    path("register/", TemplateView.as_view(
        template_name="auth/register.html"), name="register"),
    path("share/", TemplateView.as_view(
        template_name="main/share.html"), name="share"),

    # ---------- Приложение ----------
    path("dashboard/", TemplateView.as_view(
        template_name="main/dashboard.html"), name="dashboard"),
    path("casefiles/", TemplateView.as_view(
        template_name="main/casefiles.html"), name="casefiles"),
    path("personal-card/", TemplateView.as_view(
        template_name="main/personalcard.html"), name="personal_card"),

    # ---------- Upload (реални изгледи) ----------
    path("upload/", upload_page, name="upload"),
    path("upload/preview/", upload_preview, name="upload_preview"),
    path("upload/confirm/", upload_confirm, name="upload_confirm"),
    path("uploads/history/", upload_history, name="upload_history"),

    # ---------- Documents (за да не гърмят reverse-ите в темплейти/навигация) ----------
    path("documents/", TemplateView.as_view(
        template_name="subpages/upload_history.html"), name="documents"),
    path("documents/<int:pk>/", TemplateView.as_view(
        template_name="subpages/document_detail.html"), name="document_detail"),
    path("documents/<int:pk>/edit/", TemplateView.as_view(
        template_name="subpages/document_edit.html"), name="document_edit"),
    path("documents/<int:pk>/edit-tags/", TemplateView.as_view(
        template_name="subpages/document_edit_tags.html"), name="document_edit_tags"),
    path("documents/<int:pk>/move/", TemplateView.as_view(
        template_name="subpages/document_move.html"), name="document_move"),
    path("documents/<int:pk>/export/pdf/", TemplateView.as_view(
        template_name="subpages/document_export_pdf.html"), name="document_export_pdf"),

    # ---------- Events ----------
    path("events/history/", TemplateView.as_view(
        template_name="subpages/event_history.html"), name="event_history"),
    path("events/<int:pk>/", TemplateView.as_view(
        template_name="subpages/event_detail.html"), name="medical_event_detail"),
    path("events/<int:pk>/export/pdf/", TemplateView.as_view(
        template_name="subpages/event_export_pdf.html"), name="event_export_pdf"),

    # ---------- Lab ----------
    path("labtests/", TemplateView.as_view(
        template_name="subpages/labtests.html"), name="labtests"),
    path("labtests/<int:pk>/edit/", TemplateView.as_view(
        template_name="subpages/labtest_edit.html"), name="labtest_edit"),
    path("labtests/csv/print/", TemplateView.as_view(
        template_name="subpages/csv_print.html"), name="csv_print"),

    # ---------- Share (stub маршрути, за да работят всички {% url %}) ----------
    # fallback без pk (линк от навигация)
    path("share/document/", TemplateView.as_view(
        template_name="main/share.html"), name="share_document_page"),
    # с pk (линк от детайл на документ)
    path("share/document/<int:pk>/", TemplateView.as_view(
        template_name="subpages/share_view.html"), name="share_document_page"),
    # публичен изглед по токен
    path("s/<uuid:token>/", TemplateView.as_view(
        template_name="subpages/share_view.html"), name="share_view"),
    # QR PNG по токен
    path("s/<uuid:token>/qr.png", share_qr_stub, name="share_qr"),
    # създаване на share token (POST)
    path("share/create/", share_create_stub, name="share_create"),
    path("share/tokens/create/", share_create_stub, name="create_share_token"),

    # ---------- DEV: 1:1 преглед на всички темплейти ----------
    path("_tpl/auth/login/", TemplateView.as_view(
        template_name="auth/login.html"), name="tpl_auth_login"),
    path("_tpl/auth/register/", TemplateView.as_view(
        template_name="auth/register.html"), name="tpl_auth_register"),
    path("_tpl/base.html", TemplateView.as_view(
        template_name="basetemplates/base.html"), name="tpl_base"),
    path("_tpl/base_app.html", TemplateView.as_view(
        template_name="basetemplates/base_app.html"), name="tpl_base_app"),
    path("_tpl/base_public.html", TemplateView.as_view(
        template_name="basetemplates/base_public.html"), name="tpl_base_public"),
    path("_tpl/landingpage.html", TemplateView.as_view(
        template_name="basetemplates/landingpage.html"), name="tpl_landingpage"),
    path("_tpl/main/casefiles.html", TemplateView.as_view(
        template_name="main/casefiles.html"), name="tpl_main_casefiles"),
    path("_tpl/main/dashboard.html", TemplateView.as_view(
        template_name="main/dashboard.html"), name="tpl_main_dashboard"),
    path("_tpl/main/history.html", TemplateView.as_view(
        template_name="main/history.html"), name="tpl_main_history"),
    path("_tpl/main/personalcard.html", TemplateView.as_view(
        template_name="main/personalcard.html"), name="tpl_main_personalcard"),
    path("_tpl/main/share.html", TemplateView.as_view(
        template_name="main/share.html"), name="tpl_main_share"),
    path("_tpl/main/upload.html", TemplateView.as_view(
        template_name="main/upload.html"), name="tpl_main_upload"),
    path("_tpl/subpages/csv_print.html", TemplateView.as_view(
        template_name="subpages/csv_print.html"), name="tpl_sub_csv_print"),
    path("_tpl/subpages/doctors.html", TemplateView.as_view(
        template_name="subpages/doctors.html"), name="tpl_sub_doctors"),
    path("_tpl/subpages/document_detail.html", TemplateView.as_view(
        template_name="subpages/document_detail.html"), name="tpl_sub_document_detail"),
    path("_tpl/subpages/document_edit.html", TemplateView.as_view(
        template_name="subpages/document_edit.html"), name="tpl_sub_document_edit"),
    path("_tpl/subpages/document_edit_tags.html", TemplateView.as_view(
        template_name="subpages/document_edit_tags.html"), name="tpl_sub_document_edit_tags"),
    path("_tpl/subpages/document_export_pdf.html", TemplateView.as_view(
        template_name="subpages/document_export_pdf.html"), name="tpl_sub_document_export_pdf"),
    path("_tpl/subpages/document_move.html", TemplateView.as_view(
        template_name="subpages/document_move.html"), name="tpl_sub_document_move"),
    path("_tpl/subpages/event_detail.html", TemplateView.as_view(
        template_name="subpages/event_detail.html"), name="tpl_sub_event_detail"),
    path("_tpl/subpages/event_edit_tags.html", TemplateView.as_view(
        template_name="subpages/event_edit_tags.html"), name="tpl_sub_event_edit_tags"),
    path("_tpl/subpages/event_export_pdf.html", TemplateView.as_view(
        template_name="subpages/event_export_pdf.html"), name="tpl_sub_event_export_pdf"),
    path("_tpl/subpages/event_history.html", TemplateView.as_view(
        template_name="subpages/event_history.html"), name="tpl_sub_event_history"),
    path("_tpl/subpages/labtest_edit.html", TemplateView.as_view(
        template_name="subpages/labtest_edit.html"), name="tpl_sub_labtest_edit"),
    path("_tpl/subpages/labtests.html", TemplateView.as_view(
        template_name="subpages/labtests.html"), name="tpl_sub_labtests"),
    path("_tpl/subpages/medical_event_confirm_delete.html", TemplateView.as_view(
        template_name="subpages/medical_event_confirm_delete.html"), name="tpl_sub_medical_event_confirm_delete"),
    path("_tpl/subpages/medical_event_form.html", TemplateView.as_view(
        template_name="subpages/medical_event_form.html"), name="tpl_sub_medical_event_form"),
    path("_tpl/subpages/profile.html", TemplateView.as_view(
        template_name="subpages/profile.html"), name="tpl_sub_profile"),
    path("_tpl/subpages/share_view.html", TemplateView.as_view(
        template_name="subpages/share_view.html"), name="tpl_sub_share_view"),
    path("_tpl/subpages/upload_history.html", TemplateView.as_view(
        template_name="subpages/upload_history.html"), name="tpl_sub_upload_history"),

    # API за share.html – генерира двата линка
    path("share/create-links/", create_download_links, name="create_download_links"),

    # Принт изгледи (отварят се в нов таб)
    path("print/csv/", print_csv, name="print_csv"),
    path("print/pdf/", print_pdf, name="print_pdf"),

]
