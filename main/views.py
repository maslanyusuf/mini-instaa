from django.core.mail import send_mail
from django.shortcuts import render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from main.forms import SharePostForm
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


def share_post(request, post_id):
    try:
        post = Post.published.get(id=post_id)
    except Post.DoesNotExist:
        return render(request, '404.html', status=404)

    form = SharePostForm()
    sent = False
    if request.method == 'POST':
        form = SharePostForm(request.POST)
        if form.is_valid():
            post_url = request.build_absolute_uri(post.get_absolute_url())
            # Here you would typically send the email
            subject = f"{form.cleaned_data['name']} ({form.cleaned_data['email']}) recommends you read \"{post.title}\""
            message = f"Read \"{post.title}\" at {post_url}\n\n{form.cleaned_data['name']}\'s comments: {form.cleaned_data['comments']}"

            send_mail(subject, message, form.cleaned_data['email'], [form.cleaned_data['to']])
            sent = True

            # For now, we just render a success message
            return render(request, 'share_post_success.html', {'post': post, 'form': form.cleaned_data, 'sent': sent})

    return render(request, 'share_post.html', {'post': post, 'form': form})

def profile(request):
    return render(request, 'profile.html')


def explore(request):
    return render(request, 'explore.html')


def notifications(request):
    return render(request, 'notifications.html')

