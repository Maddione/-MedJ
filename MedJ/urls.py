# MedJ/urls.py

from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.conf import settings # Ensure settings is imported
from django.conf.urls.static import static # Ensure static is imported


app_name = 'medj'

urlpatterns = [
    # Public pages
    path('', views.landing_page, name='landingpage'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('register/', views.register_page, name='register'),
    path('logout/', auth_views.LogoutView.as_view(next_page='medj:landingpage'), name='logout'),

    # Authenticated pages (main navigation)
    path('dashboard/', views.dashboard_page, name='dashboard'),
    path('casefiles/', views.casefiles_page, name='casefiles'),
    path('personalcard/', views.personalcard_page, name='personalcard'),
    path('upload/', views.upload_page, name='upload_page'),

    # Patient/Document history
    path('history/', views.history_page, name='history'), # History of Medical Events
    path('upload-history/', views.upload_history_page, name='upload_history'), # History of Documents

    # Detailed view for a single Medical Event
    path('event/<int:event_id>/detail/', views.event_detail_page, name='event_detail'), # NEW: event_detail

    # Doctor-related pages
    path('doctors/', views.doctors_page, name='doctors'),

    # User profile page
    path('profile/', views.profile_page, name='profile'),

    # Other subpages (if needed, adjust views and templates)
    path('upload-review/', views.upload_review_page, name='upload_review'),

    # API endpoints
    path('api/perform-ocr/', views.perform_ocr, name='perform_ocr'),
    path('api/analyze-document/', views.analyze_document, name='analyze_document'),
    path('api/update-event-details/<int:event_id>/', views.update_event_details, name='update_event_details'),
    path('api/delete-document/<int:document_id>/', views.delete_document, name='delete_document'),

    # AJAX endpoint
    path('ajax/get-specialties/', views.get_specialties_for_category, name='get_specialties_for_category'),

    # Excel Export Endpoint
    # Corrected function name from 'export_medical_events_to_excel' to 'export_medical_events_excel'
    path('export/medical-events/', views.export_medical_events_excel, name='export_medical_events_excel'),
]

# This block should be in the main project's urls.py (e.g. MedJ2/urls2.py), not in app's urls.py
# However, if it's placed here for convenience/dev, make sure settings are correctly configured.
# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
#     urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)