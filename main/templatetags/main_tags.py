# main/templatetags/main_tags.py
from django import template
from main.models import Post
from taggit.models import Tag
from django.utils.safestring import mark_safe
import markdown

register = template.Library()

@register.simple_tag
def total_posts():
    return Post.published.count()


@register.inclusion_tag('partials/_latest_posts.html')
def show_latest_posts(count=5):
    latest_posts = Post.published.order_by('-published_at')[:count]
    return {'latest_posts': latest_posts}


@register.filter(name='markdown_format')
def markdown_format(text):
    """
    Converts Markdown text to HTML.
    """
    return mark_safe(markdown.markdown(text, extensions=['markdown.extensions.fenced_code', 'markdown.extensions.codehilite']))
