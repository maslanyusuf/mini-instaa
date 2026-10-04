from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.views.decorators.http import require_POST

from main.forms import SharePostForm,CommentForm
from .models import Post,Comment

def feed(request):
    all_posts = Post.published.all()
    # Paginate the posts, 10 per page
    paginator = Paginator(all_posts, 10)
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

    comments = post.comments.all()
    form = CommentForm()
    return render(request, 'post_detail.html', {'post': post, 'comments': comments, 'form': form})


@require_POST
def add_comment(request, post_id):
    try:
        post = Post.published.get(id=post_id)
    except Post.DoesNotExist:
        return render(request, '404.html', status=404)

    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()
        return redirect(post.get_absolute_url())

    comments = post.comments.all()
    return render(request, 'post_detail.html', {
        'post': post,
        'comments': comments,
        'form': form,
    })

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

