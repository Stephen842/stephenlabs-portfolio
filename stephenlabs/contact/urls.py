from django.urls import path
from contact import views

app_name = 'contact'

urlpatterns = [
    # Public contact page
    path('', views.contact_view, name='contact'),
    
    # Admin contact management
    path('dashboard/admin/messages/', views.contact_messages_list, name='contact_messages_list'),
    path('dashboard/admin/message/<int:message_id>/', views.contact_message_detail, name='contact_message_detail'),
    path('dashboard/admin/message/<int:message_id>/delete/', views.contact_message_delete, name='contact_message_delete'),
    path('dashboard/admin/message/<int:message_id>/update-status/', views.contact_message_update_status, name='contact_message_update_status'),
    
    # Health check
    path('health/', views.contact_health_check, name='contact_health'),
]