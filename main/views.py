from django.shortcuts import render
from .models import Post

def feed(request):
    posts = Post.published.all()
    return render(request, 'feed.html', {'posts': posts})


def post_detail(request, slug):
    try:
        post = Post.published.get(slug=slug)
    except Post.DoesNotExist:
        return render(request, '404.html', status=404)
    return render(request, 'post_detail.html', {'post': post})


def profile(request):
    return render(request, 'profile.html')


def explore(request):
    return render(request, 'explore.html')


def notifications(request):
    return render(request, 'notifications.html')

