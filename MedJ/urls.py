from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

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

    # Export URL
    path('export/medical-events/', views.export_medical_events_to_excel, name='export_medical_events_excel'),

    path('test-upload/', views.test_upload_view, name='test_upload'),
]