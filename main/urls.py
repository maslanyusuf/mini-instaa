from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.feed, name='feed'),
    path('posts/<int:year>/<int:month>/<slug:slug>/', views.post_detail, name='post_detail'),
    path('posts/<int:post_id>/share/', views.share_post, name='share_post'),
    path('posts/<int:post_id>/comment/', views.add_comment, name='add_comment'),
    path('profile/', views.profile, name='profile'),
    path('explore/', views.explore, name='explore'),
    path('notifications/', views.notifications, name='notifications'),
]
