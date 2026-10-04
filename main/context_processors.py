from taggit.models import Tag
from django.db.models import Count
from .models import Post


def all_tags(request):
    """
    Makes `all_tags` available in every template automatically.
    Only includes tags attached to published posts.
    """
    tags = (
        Tag.objects.filter(post__status=Post.Status.PUBLISHED)
        .annotate(post_count=Count('post'))
        .order_by('-post_count', 'name')
    )
    return {'all_tags': tags}
