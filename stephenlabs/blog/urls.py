from django.urls import path
from . import views

urlpatterns = [
    path('', views.post_list, name='post_list'),
    path('new/', views.post_create, name='post_create'),
    path('my-drafts/', views.my_drafts, name='my_drafts'),
    path('<slug:slug>/', views.post_detail, name='post_detail'),
    path('<slug:slug>/edit/', views.post_edit, name='post_edit'),
]