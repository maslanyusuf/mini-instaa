from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.feed, name='feed'),
    path('post/<slug:slug>/', views.post_detail, name='post_detail'),
    path('profile/', views.profile, name='profile'),
    path('explore/', views.explore, name='explore'),
    path('notifications/', views.notifications, name='notifications'),
]
