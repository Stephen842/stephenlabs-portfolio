from django.urls import path
from blog import views
from contact import views as contact_views

urlpatterns = [
    path('', views.post_list, name='post_list'),
    path('new/', views.post_create, name='post_create'),
    path('my-drafts/', views.my_drafts, name='my_drafts'),
    
    path('unsubscribe/<int:subscriber_id>/', views.unsubscribe, name='unsubscribe'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms-of-service/', views.terms_of_service, name='terms_of_service'),
    path('cookies-settings/', views.cookies, name='cookies_setting'),

    path('testing/', contact_views.testing, name='testing'),
    
    # Catch-all slug pattern MUST be LAST
    path('<slug:slug>/', views.post_detail, name='post_detail'),
    path('<slug:slug>/edit/', views.post_edit, name='post_edit'),
]