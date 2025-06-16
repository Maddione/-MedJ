from django.urls import path
from . import views

app_name = 'medj'

urlpatterns = [
    # Основни страници
    path('', views.landing_page, name='landingpage'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Страници в приложението
    path('dashboard/', views.dashboard, name='dashboard'),
    path('history/', views.upload_history, name='history'),
    path('document/<int:event_id>/', views.document_detail_view, name='document_detail'),
    path('casefiles/', views.casefiles, name='casefiles'),
    path('personalcard/', views.personalcard, name='personalcard'),
    path('profile/', views.profile, name='profile'),
    path('doctors/', views.doctors, name='doctors'),

    # Страница за качване и етапи
    path('upload/', views.upload_page, name='upload_page'),
    path('upload/review/', views.upload_review_page, name='upload_review_page'),
]