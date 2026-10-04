# main/templatetags/main_tags.py
from django import template
from main.models import Post
from taggit.models import Tag
register = template.Library()

@register.simple_tag
def total_posts():
    return Post.published.count()


@register.inclusion_tag('partials/_latest_posts.html')
def show_latest_posts(count=5):
    latest_posts = Post.published.order_by('-published_at')[:count]
    return {'latest_posts': latest_posts}
