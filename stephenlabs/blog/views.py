from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404, JsonResponse
from django.contrib import messages
from django.urls import reverse


from blog.models import Post, Category, Tag, Subscriber
from blog.utils import filter_posts, subscribe_email


def post_list(request):
    if request.method == 'POST' and 'footer_email' in request.POST:
        email = request.POST.get('footer_email')
        subscribe_email(request, email)
        messages.success(request, "Thank you! You've successfully subscribed to the StephensLab newsletter.")

    base_queryset = Post.objects.filter(
        status=Post.Status.PUBLISHED
    ).select_related('category', 'author').prefetch_related('tags')

    posts = filter_posts(request, base_queryset)

    context = {
        'posts': posts,
        'categories': Category.objects.all(),
        'tags': Tag.objects.all(),
        'selected_category': request.GET.get('category'),
        'selected_tag': request.GET.get('tag'),
        'query': request.GET.get('q'),
        'title': 'Insights & Articles · StephensLab'
    }
    return render(request, 'pages/post_list.html', context)


def post_search_ajax(request):
    '''
    Lightweight JSON search endpoint for the live navbar search dropdown.
    Returns up to 6 matching posts with the minimum fields the dropdown
    needs to render — title, slug, category, reading time, thumbnail.
    '''
    query = request.GET.get('q', '').strip()
 
    if len(query) < 2:
        return JsonResponse({'results': [], 'count': 0, 'query': query})
 
    base_queryset = Post.objects.filter(
        status=Post.Status.PUBLISHED
    ).select_related('category', 'author')
 
    # Reuse your existing filter_posts() utility for consistent search logic
    results = filter_posts(request, base_queryset)[:6]
    total_count = filter_posts(request, base_queryset).count()
 
    data = []
    for post in results:
        data.append({
            'title': post.title,
            'slug': post.slug,
            'url': reverse('post_detail', kwargs={'slug': post.slug}),
            'category': post.category.name,
            'category_slug': post.category.slug,
            'reading_time': post.reading_time,
            'excerpt': post.excerpt[:90] + ('…' if len(post.excerpt) > 90 else ''),
            'thumbnail': post.featured_image.url if post.featured_image else None,
            'initial': post.title[0].upper() if post.title else '?',
        })
 
    return JsonResponse({
        'results': data,
        'count': total_count,
        'query': query,
    })


def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug)

    if request.method == 'POST' and 'footer_email' in request.POST:
        email = request.POST.get('footer_email')
        subscribe_email(request, email)
        messages.success(request, "Thank you! You've successfully subscribed to the StephensLab newsletter.")


    # Draft protection
    if post.status == Post.Status.DRAFT:
        if not request.user.is_authenticated or post.author != request.user:
            raise Http404()
        
    query_post = filter_posts(
        request,
        Post.objects.exclude(id=post.id)
    )[:5]

    context = {
        'post': post,
        'query_post': query_post,
        'title': post.title
    }
    return render(request, 'pages/post_detail.html', context)



def unsubscribe(request, subscriber_id):
    """
    Deactivate a subscriber when they click the unsubscribe link.
    """
    subscriber = get_object_or_404(Subscriber, id=subscriber_id)

    # Mark subscriber as inactive
    subscriber.is_active = False
    subscriber.save()

    # Show a success message
    messages.success(request, f"You have been unsubscribed from StephensLab newsletter.")

    # Redirect to home page
    return redirect('post_list')


def privacy_policy(request):
    if request.method == 'POST' and 'footer_email' in request.POST:
        email = request.POST.get('footer_email')
        subscribe_email(request, email)
        messages.success(request, "Thank you! You've successfully subscribed to the StephensLab newsletter.")

    base_queryset = Post.objects.filter(
        status=Post.Status.PUBLISHED
    ).select_related('category', 'author').prefetch_related('tags')

    posts = filter_posts(request, base_queryset)

    context={
        'posts': posts,
        'categories': Category.objects.all(),
        'tags': Tag.objects.all(),
        'selected_category': request.GET.get('category'),
        'selected_tag': request.GET.get('tag'),
        'query': request.GET.get('q'),
        'title': 'Privacy Policy · StephensLab',
    }
    return render(request, 'pages/privacy_policy.html', context)

def terms_of_service(request):
    if request.method == 'POST' and 'footer_email' in request.POST:
        email = request.POST.get('footer_email')
        subscribe_email(request, email)
        messages.success(request, "Thank you! You've successfully subscribed to the StephensLab newsletter.")

    base_queryset = Post.objects.filter(
        status=Post.Status.PUBLISHED
    ).select_related('category', 'author').prefetch_related('tags')

    posts = filter_posts(request, base_queryset)

    context={
        'posts': posts,
        'categories': Category.objects.all(),
        'tags': Tag.objects.all(),
        'selected_category': request.GET.get('category'),
        'selected_tag': request.GET.get('tag'),
        'query': request.GET.get('q'),
        'title': 'Terms of Service · StephensLab',
    }
    return render(request, 'pages/terms_of_service.html', context)


def cookies(request):
    if request.method == 'POST' and 'footer_email' in request.POST:
        email = request.POST.get('footer_email')
        subscribe_email(request, email)
        messages.success(request, "Thank you! You've successfully subscribed to the StephensLab newsletter.")

    base_queryset = Post.objects.filter(
        status=Post.Status.PUBLISHED
    ).select_related('category', 'author').prefetch_related('tags')

    posts = filter_posts(request, base_queryset)

    context={
        'posts': posts,
        'categories': Category.objects.all(),
        'tags': Tag.objects.all(),
        'selected_category': request.GET.get('category'),
        'selected_tag': request.GET.get('tag'),
        'query': request.GET.get('q'),
        'title': 'Cookies Settings · StephensLab',
    }
    return render(request, 'pages/cookies_setting.html', context)