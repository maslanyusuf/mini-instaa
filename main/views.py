from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Post

def feed(request):
    all_posts = Post.published.all()
    # Paginate the posts, 10 per page
    paginator = Paginator(all_posts, 1)
    page_number = request.GET.get('page', 1)
    try:
        posts = paginator.page(page_number)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)
    return render(request, 'feed.html', {'posts': posts})


def post_detail(request, year, month, slug):
    try:
        post = Post.published.get(slug=slug, published_at__year=year, published_at__month=month)
    except Post.DoesNotExist:
        return render(request, '404.html', status=404)
    return render(request, 'post_detail.html', {'post': post})


def profile(request):
    return render(request, 'profile.html')


def explore(request):
    return render(request, 'explore.html')


def notifications(request):
    return render(request, 'notifications.html')

