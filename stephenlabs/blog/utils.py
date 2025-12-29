from django.db.models import Q
from .models import Post


def filter_posts(request, queryset=None):
    """
    Reusable blog post filtering logic.
    Can be used in views, CBVs, APIs, etc.
    """

    if queryset is None:
        queryset = Post.objects.all()

    query = request.GET.get('q')
    category_slug = request.GET.get('category')
    tag_slug = request.GET.get('tag')

    if query:
        queryset = queryset.filter(
            Q(title__icontains=query) |
            Q(excerpt__icontains=query) |
            Q(content__icontains=query)
        )

    if category_slug:
        queryset = queryset.filter(category__slug=category_slug)

    if tag_slug:
        queryset = queryset.filter(tags__slug=tag_slug)

    return queryset.distinct()