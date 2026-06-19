from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth import logout
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.views.decorators.csrf import csrf_exempt
from django.utils.safestring import mark_safe

import markdown
import os
import uuid
import logging
import cloudinary, cloudinary.uploader

from contact.models import ContactMessage
from blog.models import Post, Category, Tag, Subscriber
from lab.forms import CategoryForm, TagForm, PostForm


# ── Dashboard home ──────────────────────────────────────────────────────────
@staff_member_required
def dashboard_home(request):
    total_posts = Post.objects.count()
    published_posts = Post.objects.filter(status=Post.Status.PUBLISHED).count()
    draft_posts = Post.objects.filter(status=Post.Status.DRAFT).count()
    total_subscribers = Subscriber.objects.count()
    active_subscribers = Subscriber.objects.filter(is_active=True).count()
    new_messages = ContactMessage.objects.filter(status='new').count()
    total_messages = ContactMessage.objects.count()
    total_categories = Category.objects.count()
    total_tags = Tag.objects.count()

    recent_posts = Post.objects.select_related('category', 'author').order_by('-created_at')[:5]
    recent_messages = ContactMessage.objects.order_by('-created_at')[:5]

    context = {
        'total_posts': total_posts,
        'published_posts': published_posts,
        'draft_posts': draft_posts,
        'total_subscribers': total_subscribers,
        'active_subscribers': active_subscribers,
        'new_messages': new_messages,
        'total_messages': total_messages,
        'total_categories': total_categories,
        'total_tags': total_tags,
        'recent_posts': recent_posts,
        'recent_messages': recent_messages,
        'title': 'Dashboard · StephensLab',
    }
    return render(request, 'pages/dashboard_home.html', context)


@staff_member_required
def post_create(request):
    """Create a new blog post"""
 
    if request.method == 'POST':
        # request.FILES must be passed or the uploaded image
        # never reaches form.cleaned_data / instance.featured_image
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            if post.status == Post.Status.PUBLISHED and not post.published_at:
                post.published_at = timezone.now()
            post.save()
 
            # ── FIX: was form.save_m2m() — does nothing for 'tags' since
            # it's a form-only field, not in Meta.fields, so ModelForm
            # never registered it as an m2m field to manage. Use the
            # explicit save_tags() method on PostForm instead. ──
            form.save_tags(post)
 
            messages.success(request, f'Post "{post.title}" created successfully.')
            return redirect('lab:post_edit', post_id=post.id)
    else:
        form = PostForm()
 
    context = {
        'form': form,
        'categories': Category.objects.all(),
        'tags': Tag.objects.all(),
        'title': 'Create New Post',
        'is_edit': False,
    }
    return render(request, 'pages/admin_post_form.html', context)
 
 
@staff_member_required
def post_edit(request, post_id):
    """Edit an existing blog post"""
 
    post = get_object_or_404(Post, id=post_id)
 
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            updated_post = form.save(commit=False)
            if updated_post.status == Post.Status.PUBLISHED and not updated_post.published_at:
                updated_post.published_at = timezone.now()
            updated_post.save()
 
            # ── FIX: was form.save_m2m() — same issue as post_create above. ──
            form.save_tags(updated_post)
 
            messages.success(request, f'Post "{updated_post.title}" updated successfully.')
            return redirect('lab:post_edit', post_id=post.id)
    else:
        form = PostForm(instance=post)
 
    context = {
        'form': form,
        'post': post,
        'categories': Category.objects.all(),
        'tags': Tag.objects.all(),
        'title': 'Edit Post',
        'is_edit': True,
    }
    return render(request, 'pages/admin_post_form.html', context)
 
 
@staff_member_required
def post_preview(request, post_id):
    '''Preview a blog post before publishing'''
    post = get_object_or_404(Post, id=post_id)
    return render(request, 'pages/admin_post_preview.html', {'post': post})
 
 
@staff_member_required
@require_http_methods(['POST'])
def post_preview_ajax(request):
    """AJAX endpoint for live preview while editing"""
    content = request.POST.get('content', '')
    title = request.POST.get('title', 'Preview')
 
    try:
        html_content = markdown.markdown(content, extensions=['fenced_code', 'codehilite'])
    except Exception:
        html_content = content.replace('\n', '<br>')
 
    return JsonResponse({
        'title': title,
        'content': html_content,
        'reading_time': max(1, len(content.split()) // 200)
    })


# ── Blog: post list ─────────────────────────────────────────────────────────
@staff_member_required
def dashboard_post_list(request):
    status_filter = request.GET.get('status', '')
    category_filter = request.GET.get('category', '')
    search_query = request.GET.get('q', '')

    posts_qs = Post.objects.select_related('category', 'author').prefetch_related('tags')

    if status_filter:
        posts_qs = posts_qs.filter(status=status_filter)
    if category_filter:
        posts_qs = posts_qs.filter(category__slug=category_filter)
    if search_query:
        posts_qs = posts_qs.filter(
            Q(title__icontains=search_query) |
            Q(excerpt__icontains=search_query) |
            Q(author__username__icontains=search_query)
        )

    paginator  = Paginator(posts_qs, 25)
    page_obj   = paginator.get_page(request.GET.get('page', 1))

    context = {
        'posts': page_obj,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'search_query': search_query,
        'categories': Category.objects.all(),
        'total_posts': Post.objects.count(),
        'published_count': Post.objects.filter(status=Post.Status.PUBLISHED).count(),
        'draft_count': Post.objects.filter(status=Post.Status.DRAFT).count(),
        'title': 'Posts · Dashboard',
    }
    return render(request, 'pages/admin_blog_posts.html', context)


# ── Blog: toggle publish status (AJAX) ─────────────────────────────────────
@staff_member_required
@require_http_methods(['POST'])
def dashboard_post_toggle_status(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if post.status == Post.Status.PUBLISHED:
        post.status = Post.Status.DRAFT
        post.published_at = None
    else:
        post.status = Post.Status.PUBLISHED
        if not post.published_at:
            post.published_at = timezone.now()
    post.save(update_fields=['status', 'published_at', 'updated_at'])
    return JsonResponse({'success': True, 'new_status': post.status, 'label': post.get_status_display()})


# ── Blog: delete post ───────────────────────────────────────────────────────
@staff_member_required
def dashboard_post_delete(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.method == 'POST':
        title = post.title
        post.delete()
        messages.success(request, f"'{title}' has been permanently deleted.")
        return redirect('lab:dashboard_post_list')
    return render(request, 'pages/admin_blog_post_delete.html', {'post': post})


# ── Subscribers ─────────────────────────────────────────────────────────────
@staff_member_required
def dashboard_subscribers(request):
    filter_active = request.GET.get('active', '')
    search_query  = request.GET.get('q', '')

    subs_qs = Subscriber.objects.all().order_by('-created_at')

    if filter_active == '1':
        subs_qs = subs_qs.filter(is_active=True)
    elif filter_active == '0':
        subs_qs = subs_qs.filter(is_active=False)
    if search_query:
        subs_qs = subs_qs.filter(email__icontains=search_query)

    paginator = Paginator(subs_qs, 50)
    page_obj  = paginator.get_page(request.GET.get('page', 1))

    context = {
        'subscribers': page_obj,
        'filter_active': filter_active,
        'search_query': search_query,
        'total_count': Subscriber.objects.count(),
        'active_count': Subscriber.objects.filter(is_active=True).count(),
        'inactive_count': Subscriber.objects.filter(is_active=False).count(),
        'title': 'Subscribers · Dashboard',
    }
    return render(request, 'pages/admin_subscribers.html', context)


# ── Subscriber: toggle active (AJAX) ───────────────────────────────────────
@staff_member_required
@require_http_methods(['POST'])
def dashboard_subscriber_toggle(request, subscriber_id):
    sub = get_object_or_404(Subscriber, id=subscriber_id)
    sub.is_active = not sub.is_active
    sub.save(update_fields=['is_active'])
    return JsonResponse({'success': True, 'is_active': sub.is_active})


# ── Subscriber: delete (AJAX or form) ──────────────────────────────────────
@staff_member_required
def dashboard_subscriber_delete(request, subscriber_id):
    '''Delete a subscriber and redirect back to list'''
    subscriber = get_object_or_404(Subscriber, id=subscriber_id)
    
    if request.method == 'POST':
        email = subscriber.email
        subscriber.delete()
        messages.success(request, f"Subscriber '{email}' has been removed successfully.")
        return redirect('lab:dashboard_subscribers')
    
    # If GET request, redirect to list
    return redirect('lab:dashboard_subscribers')


# ── Category views ──────────────────────────────────────────────────────────
@staff_member_required
def category_list(request):
    '''List all categories'''
    categories = Category.objects.prefetch_related('posts').all().order_by('name')
    return render(request, 'pages/admin_categories.html', {'categories': categories})


@staff_member_required
def category_create(request):
    '''Create a new category'''
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f"Category '{category.name}' created successfully.")
            return redirect('lab:category_list')
    else:
        form = CategoryForm()
    
    return render(request, 'pages/admin_category_form.html', {'form': form, 'title': 'Create Category'})


@staff_member_required
def category_edit(request, category_id):
    '''Edit an existing category'''
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save()
            messages.success(request, f"Category '{category.name}' updated successfully.")
            return redirect('lab:category_list')
    else:
        form = CategoryForm(instance=category)
    
    return render(request, 'pages/admin_category_form.html', {'form': form, 'category': category, 'title': 'Edit Category'})


@staff_member_required
def category_delete(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == 'POST':
        if category.posts.count() == 0:
            category.delete()
            messages.success(request, f"Category '{category.name}' deleted successfully.")
        else:
            messages.error(request, f"Cannot delete '{category.name}' because it has {category.posts.count()} post(s) assigned.")
        return redirect('lab:category_list')
    
    # If GET request, redirect to list
    return redirect('lab:category_list')


# ── Tag views ──────────────────────────────────────────────────────────────
@staff_member_required
def tag_list(request):
    '''List all tags'''
    tags = Tag.objects.prefetch_related('posts').all().order_by('name')
    return render(request, 'pages/admin_tags.html', {'tags': tags})


@staff_member_required
def tag_create(request):
    '''Create a new tag'''
    if request.method == 'POST':
        form = TagForm(request.POST)
        if form.is_valid():
            tag = form.save()
            messages.success(request, f"Tag '{tag.name}' created successfully.")
            return redirect('lab:tag_list')
    else:
        form = TagForm()
    
    return render(request, 'pages/admin_tag_form.html', {'form': form, 'title': 'Create Tag'})


@staff_member_required
def tag_edit(request, tag_id):
    '''Edit an existing tag'''
    tag = get_object_or_404(Tag, id=tag_id)
    
    if request.method == 'POST':
        form = TagForm(request.POST, instance=tag)
        if form.is_valid():
            tag = form.save()
            messages.success(request, f"Tag '{tag.name}' updated successfully.")
            return redirect('lab:tag_list')
    else:
        form = TagForm(instance=tag)
    
    return render(request, 'pages/admin_tag_form.html', {'form': form, 'tag': tag, 'title': 'Edit Tag'})


@staff_member_required
def tag_delete(request, tag_id):
    tag = get_object_or_404(Tag, id=tag_id)
    
    if request.method == 'POST':
        tag.delete()
        messages.success(request, f"Tag '{tag.name}' deleted successfully.")
        return redirect('lab:tag_list')
    
    # If GET request, redirect to list
    return redirect('lab:tag_list')


logger = logging.getLogger(__name__)
 
ALLOWED_TYPES = {
    # Images
    'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml',
    # Documents
    'application/pdf',
    # Video
    'video/mp4', 'video/webm',
    # Audio
    'audio/mpeg', 'audio/wav', 'audio/ogg',
}
 
MAX_SIZE_BYTES = 20 * 1024 * 1024  # 20MB for video/media, reasonable for all types


@staff_member_required
@csrf_exempt
@require_http_methods(['POST'])
def tinymce_upload(request):
    '''
    Handle TinyMCE file uploads (images, documents, media) via Cloudinary.
    Called from the file_picker_callback configured in TINYMCE_DEFAULT_CONFIG.
 
    TinyMCE expects back:  {"location": "<public_url>"}
    On error it expects:   {"error": "<message>"} with a 4xx/5xx status.
    '''
    file_obj = request.FILES.get('file')
 
    if not file_obj:
        return JsonResponse({'error': 'No file received.'}, status=400)
 
    if file_obj.content_type not in ALLOWED_TYPES:
        return JsonResponse(
            {'error': f'File type "{file_obj.content_type}" is not allowed.'},
            status=400
        )
 
    if file_obj.size > MAX_SIZE_BYTES:
        return JsonResponse(
            {'error': f'File exceeds the {MAX_SIZE_BYTES // (1024*1024)}MB size limit.'},
            status=400
        )
 
    try:
        result = cloudinary.uploader.upload(
            file_obj,
            folder='stephenslab/posts',
            resource_type='auto',
            access_mode='public',
            use_filename=False,
            unique_filename=True,
        )
        return JsonResponse({'location': result['secure_url']})
 
    except cloudinary.exceptions.Error as e:
        logger.error('Cloudinary upload failed: %s', str(e))
        return JsonResponse({'error': 'Upload failed. Please try again.'}, status=500)
 
    except Exception as e:
        logger.exception('Unexpected error during TinyMCE upload')
        return JsonResponse({'error': 'An unexpected error occurred.'}, status=500)


def custom_logout(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('/')