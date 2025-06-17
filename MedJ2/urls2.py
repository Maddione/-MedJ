from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns, set_language # NEW: Import set_language

urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/', set_language, name='set_language'), # NEW: Add this line for language switching
    *i18n_patterns(
        path('', include('MedJ.urls')),
        prefix_default_language=True
    )
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)