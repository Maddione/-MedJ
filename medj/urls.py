from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import set_language
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("i18n/setlang/", set_language, name="set_language"),
    path("", include("records.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
