from django.urls import path
from . import views

app_name = 'medj'

urlpatterns = [
    path('', views.landing_page, name='landingpage'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('history/', views.upload_history, name='history'),
    path('document/<int:doc_id>/', views.document_detail_view, name='document_detail'),
    path('casefiles/', views.casefiles, name='casefiles'),
    path('personalcard/', views.personalcard, name='personalcard'),
    path('profile/', views.profile, name='profile'),
    path('doctors/', views.doctors, name='doctors'),
    path('upload/', views.upload_page, name='upload'),
    path('api/perform-ocr/', views.perform_ocr, name='perform_ocr'),
    path('api/analyze-document/', views.analyze_document, name='analyze_document'),
]