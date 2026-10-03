from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.feed, name='feed'),
    path('post/<int:year>/<int:month>/<slug:slug>/', views.post_detail, name='post_detail'),
    path('share/<int:post_id>/', views.share_post, name='share_post'),
    path('profile/', views.profile, name='profile'),
    path('explore/', views.explore, name='explore'),
    path('notifications/', views.notifications, name='notifications'),
]
