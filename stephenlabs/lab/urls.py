from django.urls import path
from lab import views

app_name = 'lab'

urlpatterns = [
    # Dashboard home
    path('', views.dashboard_home, name='dashboard_home'),
    
    # Posts
    path('posts/', views.dashboard_post_list, name='dashboard_post_list'),
    path('posts/create/', views.post_create, name='post_create'),
    path('posts/<int:post_id>/edit/', views.post_edit, name='post_edit'),
    path('posts/<int:post_id>/preview/', views.post_preview, name='post_preview'),
    path('posts/preview-ajax/', views.post_preview_ajax, name='post_preview_ajax'),
    path('posts/<int:post_id>/toggle-status/', views.dashboard_post_toggle_status, name='dashboard_post_toggle_status'),
    path('posts/<int:post_id>/delete/', views.dashboard_post_delete, name='dashboard_post_delete'),

    # Subscribers
    path('subscribers/', views.dashboard_subscribers, name='dashboard_subscribers'),
    path('subscribers/<int:subscriber_id>/toggle/', views.dashboard_subscriber_toggle, name='dashboard_subscriber_toggle'),
    path('subscribers/<int:subscriber_id>/delete/', views.dashboard_subscriber_delete, name='dashboard_subscriber_delete'),
    
    # Categories (new CRUD)
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:category_id>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:category_id>/delete/', views.category_delete, name='category_delete'),
    
    # Tags (new CRUD)
    path('tags/', views.tag_list, name='tag_list'),
    path('tags/create/', views.tag_create, name='tag_create'),
    path('tags/<int:tag_id>/edit/', views.tag_edit, name='tag_edit'),
    path('tags/<int:tag_id>/delete/', views.tag_delete, name='tag_delete'),

    # Logout
    path('logout/', views.custom_logout, name='logout'),
]