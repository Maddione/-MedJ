from django.urls import path
from records.views.api_upload import upload_ocr, upload_analyze, upload_confirm, events_suggest
from records.views.share_api import share_create, share_history, share_revoke, share_qr_png

urlpatterns = [
    path("upload/ocr/", upload_ocr, name="upload_ocr"),
    path("upload/analyze/", upload_analyze, name="upload_analyze"),
    path("upload/confirm/", upload_confirm, name="upload_confirm"),
    path("events/suggest/", events_suggest, name="events_suggest"),

    path("share/create/", share_create, name="share_create"),
    path("share/history/", share_history, name="share_history_api"),
    path("share/revoke/<str:token>/", share_revoke, name="share_revoke"),
    path("share/qr/<str:token>.png", share_qr_png, name="share_qr_png"),
]
