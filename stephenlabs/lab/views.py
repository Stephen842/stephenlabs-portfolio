from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q,  Sum, Count
from django.contrib import messages
from django.contrib.auth import logout
from django.conf import settings
from django.core.files.storage import default_storage
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import EmailMultiAlternatives
from django.db.models.functions import TruncDate, TruncMonth
import json
from datetime import timedelta

import markdown
import logging
import cloudinary, cloudinary.uploader

from contact.models import ContactMessage
from blog.models import Post, Category, Tag, Subscriber
from lab.models import Campaign, CampaignRecipient, CampaignTemplate, EmailSegment, CampaignAnalytics, EmailTracking
from lab.forms import CategoryForm, TagForm, PostForm, CampaignForm, CampaignTemplateForm


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
    '''Create a new blog post'''
 
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
 
            messages.success(request, f"Post '{post.title}' created successfully.")
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
    '''Edit an existing blog post'''
 
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
 
            messages.success(request, f"Post '{updated_post.title}' updated successfully.")
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
    '''AJAX endpoint for live preview while editing'''
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
 
    TinyMCE expects back:  {'location': '<public_url>'}
    On error it expects:   {'error': '<message>'} with a 4xx/5xx status.
    '''
    file_obj = request.FILES.get('file')
 
    if not file_obj:
        return JsonResponse({'error': 'No file received.'}, status=400)
 
    if file_obj.content_type not in ALLOWED_TYPES:
        return JsonResponse(
            {'error': f"File type '{file_obj.content_type}' is not allowed."},
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


# ── Campaign List ──────────────────────────────────────────────────────────
@staff_member_required
def campaign_list(request):
    '''List all campaigns'''
    
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('q', '')
    
    campaigns_qs = Campaign.objects.select_related('created_by').all()
    
    if status_filter:
        campaigns_qs = campaigns_qs.filter(status=status_filter)
    if search_query:
        campaigns_qs = campaigns_qs.filter(
            Q(subject__icontains=search_query) |
            Q(tags__icontains=search_query)
        )
    
    paginator = Paginator(campaigns_qs, 25)
    page = paginator.get_page(request.GET.get('page', 1))

    # Get all counts for the stats strip
    total_count = Campaign.objects.count()
    draft_count = Campaign.objects.filter(status=Campaign.Status.DRAFT).count()
    scheduled_count = Campaign.objects.filter(status=Campaign.Status.SCHEDULED).count()
    sent_count = Campaign.objects.filter(status=Campaign.Status.SENT).count()
    failed_count = Campaign.objects.filter(status=Campaign.Status.FAILED).count()
    
    context = {
        'campaigns': page,
        'status_filter': status_filter,
        'search_query': search_query,
        'total_count': total_count,
        'draft_count': draft_count,
        'scheduled_count': scheduled_count,
        'sent_count': sent_count,
        'failed_count': failed_count,
        
        # Sidebar counts
        'draft_count_sidebar': Campaign.objects.filter(status=Campaign.Status.DRAFT).count(),
        
        'new_message_count': ContactMessage.objects.filter(status='new').count(),
        'title': 'Email Campaigns · Dashboard',
    }
    return render(request, 'pages/campaign_list.html', context)


# ── Campaign Create ───────────────────────────────────────────────────────
@staff_member_required
def campaign_create(request):
    '''Create a new campaign'''
    
    if request.method == 'POST':
        form = CampaignForm(request.POST)
        if form.is_valid():
            campaign = form.save(commit=False)
            campaign.created_by = request.user
            campaign.total_recipients = Subscriber.objects.filter(is_active=True).count()
            campaign.save()
            form.save_m2m()
            
            messages.success(request, f"Campaign '{campaign.subject}' created successfully.")
            return redirect('lab:campaign_edit', campaign_id=campaign.id)
    else:
        form = CampaignForm(initial={
            'from_email': 'Stephenslab001@gmail.com',
            'from_name': 'The StephensLab Team',
            'reply_to': 'Stephenslab001@gmail.com',
        })
    
    context = {
        'form': form,
        'title': 'Create Campaign',
        'is_edit': False,
        'draft_count': Campaign.objects.filter(status=Campaign.Status.DRAFT).count(),
        'new_message_count': ContactMessage.objects.filter(status='new').count(),
        'subscriber_count': Subscriber.objects.filter(is_active=True).count(),
    }
    return render(request, 'pages/campaign_form.html', context)


# ── Campaign Edit ──────────────────────────────────────────────────────────
@staff_member_required
def campaign_edit(request, campaign_id):
    '''Edit an existing campaign'''
    
    campaign = get_object_or_404(Campaign, id=campaign_id)
    
    if request.method == 'POST':
        form = CampaignForm(request.POST, instance=campaign)
        if form.is_valid():
            campaign = form.save()
            messages.success(request, f"Campaign '{campaign.subject}' updated successfully.")
            return redirect('lab:campaign_edit', campaign_id=campaign.id)
    else:
        form = CampaignForm(instance=campaign)
    
    context = {
        'form': form,
        'campaign': campaign,
        'title': 'Edit Campaign',
        'is_edit': True,
        'draft_count': Campaign.objects.filter(status=Campaign.Status.DRAFT).count(),
        'new_message_count': ContactMessage.objects.filter(status='new').count(),
        'subscriber_count': Subscriber.objects.filter(is_active=True).count(),
    }
    return render(request, 'pages/campaign_form.html', context)


# ── Campaign Preview ──────────────────────────────────────────────────────
@staff_member_required
def campaign_preview(request, campaign_id):
    '''Preview a campaign'''
    
    campaign = get_object_or_404(Campaign, id=campaign_id)
    context = {
        'campaign': campaign,
        'draft_count': Campaign.objects.filter(status=Campaign.Status.DRAFT).count(),
        'new_message_count': ContactMessage.objects.filter(status='new').count(),
    }
    return render(request, 'pages/campaign_preview.html', context)


# ── Campaign Send ──────────────────────────────────────────────────────────
@staff_member_required
@require_http_methods(['POST'])
def campaign_send(request, campaign_id):
    '''Send a campaign to all active subscribers'''
    
    campaign = get_object_or_404(Campaign, id=campaign_id)
    
    if campaign.status in [Campaign.Status.SENT, Campaign.Status.SENDING]:
        messages.error(request, 'This campaign has already been sent or is currently being sent.')
        return redirect('lab:campaign_detail', campaign_id=campaign.id)
    
    # Get all active subscribers
    subscribers = Subscriber.objects.filter(is_active=True)
    
    if not subscribers.exists():
        messages.error(request, 'No active subscribers to send to.')
        return redirect('lab:campaign_edit', campaign_id=campaign.id)
    
    # Update campaign status
    campaign.status = Campaign.Status.SENDING
    campaign.sent_at = timezone.now()
    campaign.total_recipients = subscribers.count()
    campaign.save()
    
    # Process sending (in a real app, this would be a background task)
    try:
        sent_count = send_campaign_emails(campaign, subscribers)
        campaign.sent_count = sent_count

        # Only mark as SENT if at least one email was sent
        if sent_count > 0:
            campaign.status = Campaign.Status.SENT
            CampaignAnalytics.objects.create(campaign=campaign)
            messages.success(request, f'Campaign sent to {sent_count} subscribers.')
        else:
            campaign.status = Campaign.Status.FAILED
            messages.error(request, 'Campaign failed to send to any subscribers.')

        campaign.save()
        
    except Exception as e:
        # Ensure campaign is marked as FAILED
        campaign.status = Campaign.Status.FAILED
        campaign.save()
        messages.error(request, f'Failed to send campaign: {str(e)}')
    
    return redirect('lab:campaign_detail', campaign_id=campaign.id)


# ── Campaign Detail ──────────────────────────────────────────────────────
@staff_member_required
def campaign_detail(request, campaign_id):
    '''View campaign details and analytics'''
    
    campaign = get_object_or_404(Campaign, id=campaign_id)
    analytics = CampaignAnalytics.objects.filter(campaign=campaign).first()
    recent_recipients = CampaignRecipient.objects.filter(
        campaign=campaign
    ).select_related('subscriber')[:20]
    
    context = {
        'campaign': campaign,
        'analytics': analytics,
        'recent_recipients': recent_recipients,
        'open_rate': campaign.get_open_rate(),
        'click_rate': campaign.get_click_rate(),
        'bounce_rate': campaign.get_bounce_rate(),
        'unsubscribe_rate': campaign.get_unsubscribe_rate(),
        'draft_count': Campaign.objects.filter(status=Campaign.Status.DRAFT).count(),
        'new_message_count': ContactMessage.objects.filter(status='new').count(),
        'title': f'{campaign.subject} · Campaign',
    }
    return render(request, 'pages/campaign_detail.html', context)


# ── Campaign Delete ──────────────────────────────────────────────────────
@staff_member_required
def campaign_delete(request, campaign_id):
    '''Delete a campaign'''
    
    campaign = get_object_or_404(Campaign, id=campaign_id)
    
    if request.method == 'POST':
        campaign.delete()
        messages.success(request, 'Campaign deleted successfully.')
        return redirect('lab:campaign_list')
    
    context = {
        'campaign': campaign,
        'draft_count': Campaign.objects.filter(status=Campaign.Status.DRAFT).count(),
        'new_message_count': ContactMessage.objects.filter(status='new').count(),
    }
    return render(request, 'pages/campaign_delete.html', context)


# ── Template List ──────────────────────────────────────────────────────────
@staff_member_required
def template_list(request):
    '''List all email templates'''
    
    templates = CampaignTemplate.objects.filter(is_active=True).order_by('name')
    
    context = {
        'templates': templates,
        'draft_count': Campaign.objects.filter(status=Campaign.Status.DRAFT).count(),
        'new_message_count': ContactMessage.objects.filter(status='new').count(),
        'title': 'Email Templates · Dashboard',
    }
    return render(request, 'pages/template_list.html', context)


# ── Template Create ──────────────────────────────────────────────────────
@staff_member_required
def template_create(request):
    '''Create a new email template'''
    
    if request.method == 'POST':
        form = CampaignTemplateForm(request.POST)
        if form.is_valid():
            template = form.save(commit=False)
            template.created_by = request.user
            template.save()
            messages.success(request, f"Template '{template.name}' created successfully.")
            return redirect('lab:template_list')
    else:
        form = CampaignTemplateForm()
    
    context = {
        'form': form,
        'title': 'Create Template',
        'draft_count': Campaign.objects.filter(status=Campaign.Status.DRAFT).count(),
        'new_message_count': ContactMessage.objects.filter(status='new').count(),
    }
    return render(request, 'pages/template_form.html', context)


# ── Template Edit ──────────────────────────────────────────────────────────
@staff_member_required
def template_edit(request, template_id):
    '''Edit an existing email template'''
    
    template = get_object_or_404(CampaignTemplate, id=template_id)
    
    if request.method == 'POST':
        form = CampaignTemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, f"Template '{template.name}' updated successfully.")
            return redirect('lab:template_list')
    else:
        form = CampaignTemplateForm(instance=template)
    
    context = {
        'form': form,
        'template': template,
        'title': 'Edit Template',
        'draft_count': Campaign.objects.filter(status=Campaign.Status.DRAFT).count(),
        'new_message_count': ContactMessage.objects.filter(status='new').count(),
    }
    return render(request, 'pages/template_form.html', context)


# ── Template Delete ──────────────────────────────────────────────────────
@staff_member_required
def template_delete(request, template_id):
    '''Delete a template'''
    
    template = get_object_or_404(CampaignTemplate, id=template_id)
    
    if request.method == 'POST':
        template.delete()
        messages.success(request, 'Template deleted successfully.')
        return redirect('lab:template_list')
    
    context = {
        'template': template,
        'draft_count': Campaign.objects.filter(status=Campaign.Status.DRAFT).count(),
        'new_message_count': ContactMessage.objects.filter(status='new').count(),
    }
    return render(request, 'pages/template_delete.html', context)


# ── Helper Function: Send Campaign Emails ──────────────────────────────
def send_campaign_emails(campaign, subscribers):
    '''Send campaign emails to subscribers'''
    
    sent_count = 0
    failed_count = 0
    
    for subscriber in subscribers:
        try:
            first_name = subscriber.email.split('@')[0] if subscriber.email else 'Reader'

            # Prepare email context with personalization
            context = {
                'campaign': campaign,
                'subscriber': subscriber,
                'email': subscriber.email,
                'first_name': first_name,
                'full_name': subscriber.email,
                'unsubscribe_url': f'/unsubscribe/{subscriber.id}/',
                'tracking_pixel_url': f'/lab/track/open/{campaign.id}/{subscriber.id}/',
                'campaign_id': campaign.id,
                'year': timezone.now().year,
            }
            
            # Render email body with personalization
            html_body = campaign.body
            # Replace personalization tags
            for key, value in context.items():
                if isinstance(value, str):
                    html_body = html_body.replace(f'{{{{ {key} }}}}', value)
                elif isinstance(value, (int, float)):
                    html_body = html_body.replace(f'{{{{ {key} }}}}', str(value))
            
            # Create email
            email = EmailMultiAlternatives(
                subject=campaign.subject,
                body='',  # Plain text version can be generated from HTML
                from_email=f'{campaign.from_name} <{campaign.from_email}>',
                to=[subscriber.email],
                reply_to=[campaign.reply_to],
            )
            
            # Attach HTML version
            email.attach_alternative(html_body, 'text/html')
            
            # Send email
            email.send(fail_silently=False)
            
            # Record successful send
            CampaignRecipient.objects.create(
                campaign=campaign,
                subscriber=subscriber,
                status=CampaignRecipient.Status.SENT,
                sent_at=timezone.now()
            )
            
            sent_count += 1
            
        except Exception as e:
            failed_count += 1
            
            # Record failed attempt
            CampaignRecipient.objects.create(
                campaign=campaign,
                subscriber=subscriber,
                status=CampaignRecipient.Status.FAILED,
                error_message=str(e)[:500],
                sent_at=timezone.now()
            )
    
    return sent_count


# ── Tracking Endpoint: Open Tracking ──────────────────────────────────
@csrf_exempt
def track_open(request, campaign_id, subscriber_id):
    '''Track email opens'''
    
    if request.method == 'GET':
        try:
            campaign = get_object_or_404(Campaign, id=campaign_id)
            subscriber = get_object_or_404(Subscriber, id=subscriber_id)
            
            recipient = CampaignRecipient.objects.filter(
                campaign=campaign,
                subscriber=subscriber
            ).first()
            
            if recipient and recipient.status != CampaignRecipient.Status.OPENED:
                recipient.status = CampaignRecipient.Status.OPENED
                recipient.opened_at = timezone.now()
                recipient.save()
                
                # Create tracking event
                EmailTracking.objects.create(
                    campaign=campaign,
                    recipient=recipient,
                    event_type=EmailTracking.EventType.OPEN,
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    metadata={'user_agent': request.META.get('HTTP_USER_AGENT', '')}
                )
                
                # Update campaign stats
                campaign.opened_count += 1
                campaign.save()
                
                # Return transparent 1x1 pixel
                response = HttpResponse(content_type='image/gif')
                response.write(b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b')
                return response
                
        except Exception as e:
            pass
    
    return HttpResponse(status=204)


# ── Tracking Endpoint: Click Tracking ──────────────────────────────────
@csrf_exempt
def track_click(request, campaign_id, subscriber_id):
    '''Track email clicks'''
    
    if request.method == 'GET':
        url = request.GET.get('url', '')
        
        try:
            campaign = get_object_or_404(Campaign, id=campaign_id)
            subscriber = get_object_or_404(Subscriber, id=subscriber_id)
            
            recipient = CampaignRecipient.objects.filter(
                campaign=campaign,
                subscriber=subscriber
            ).first()
            
            if recipient:
                if recipient.status != CampaignRecipient.Status.CLICKED:
                    recipient.status = CampaignRecipient.Status.CLICKED
                    recipient.clicked_at = timezone.now()
                    recipient.save()
                
                # Track clicked link
                if url:
                    links = recipient.clicked_links or []
                    if url not in links:
                        links.append(url)
                        recipient.clicked_links = links
                        recipient.save()
                
                # Create tracking event
                EmailTracking.objects.create(
                    campaign=campaign,
                    recipient=recipient,
                    event_type=EmailTracking.EventType.CLICK,
                    url=url,
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    metadata={'url': url}
                )
                
                # Update campaign stats
                campaign.clicked_count += 1
                campaign.save()
                
        except Exception as e:
            pass
    
    # Redirect to the target URL
    if url:
        return redirect(url)
    return redirect('/')


def get_client_ip(request):
    '''Get client IP address'''
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# ── Subscriber Segments ──────────────────────────────────────────────────
@staff_member_required
def segment_list(request):
    '''List all subscriber segments'''
    
    segments = EmailSegment.objects.all().order_by('name')
    
    context = {
        'segments': segments,
        'draft_count': Campaign.objects.filter(status=Campaign.Status.DRAFT).count(),
        'new_message_count': ContactMessage.objects.filter(status='new').count(),
        'title': 'Subscriber Segments · Dashboard',
    }
    return render(request, 'pages/segment_list.html', context)


# ── Tracking Stats ──────────────────────────────────────────────────────────
@staff_member_required
def tracking_stats(request):
    '''View comprehensive campaign tracking statistics'''
    
    # ── Basic Campaign Stats ──────────────────────────────────────────
    total_campaigns = Campaign.objects.count()
    sent_campaigns = Campaign.objects.filter(status=Campaign.Status.SENT).count()
    draft_campaigns = Campaign.objects.filter(status=Campaign.Status.DRAFT).count()
    failed_campaigns = Campaign.objects.filter(status=Campaign.Status.FAILED).count()
    scheduled_campaigns = Campaign.objects.filter(status=Campaign.Status.SCHEDULED).count()
    
    # ── Delivery Stats ─────────────────────────────────────────────────
    total_sent = Campaign.objects.filter(status=Campaign.Status.SENT).aggregate(
        total=Sum('sent_count')
    )['total'] or 0
    
    total_recipients = Campaign.objects.filter(status=Campaign.Status.SENT).aggregate(
        total=Sum('total_recipients')
    )['total'] or 0
    
    total_bounced = Campaign.objects.filter(status=Campaign.Status.SENT).aggregate(
        total=Sum('bounced_count')
    )['total'] or 0
    
    total_unsubscribed = Campaign.objects.filter(status=Campaign.Status.SENT).aggregate(
        total=Sum('unsubscribe_count')
    )['total'] or 0
    
    # ── Engagement Stats ───────────────────────────────────────────────
    total_opens = Campaign.objects.filter(status=Campaign.Status.SENT).aggregate(
        total=Sum('opened_count')
    )['total'] or 0
    
    total_clicks = Campaign.objects.filter(status=Campaign.Status.SENT).aggregate(
        total=Sum('clicked_count')
    )['total'] or 0
    
    # ── Rate Calculations ──────────────────────────────────────────────
    overall_open_rate = (total_opens / total_sent * 100) if total_sent > 0 else 0
    overall_click_rate = (total_clicks / total_sent * 100) if total_sent > 0 else 0
    overall_bounce_rate = (total_bounced / total_sent * 100) if total_sent > 0 else 0
    overall_unsubscribe_rate = (total_unsubscribed / total_sent * 100) if total_sent > 0 else 0
    
    # ── Recent Campaigns (last 30 days) ──────────────────────────────
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_campaigns = Campaign.objects.filter(
        status=Campaign.Status.SENT,
        sent_at__gte=thirty_days_ago
    ).order_by('-sent_at')
    
    # ── Daily Stats for Chart ──────────────────────────────────────────
    daily_stats = Campaign.objects.filter(
        status=Campaign.Status.SENT,
        sent_at__gte=thirty_days_ago
    ).annotate(
        date=TruncDate('sent_at')
    ).values('date').annotate(
        sent=Sum('sent_count'),
        opens=Sum('opened_count'),
        clicks=Sum('clicked_count'),
        bounces=Sum('bounced_count'),
        unsubscribes=Sum('unsubscribe_count')
    ).order_by('date')
    
    # ── Campaign Performance ───────────────────────────────────────────
    campaign_performance = []
    for campaign in recent_campaigns[:20]:
        campaign_performance.append({
            'id': campaign.id,
            'subject': campaign.subject,
            'sent': campaign.sent_count,
            'opens': campaign.opened_count,
            'clicks': campaign.clicked_count,
            'open_rate': campaign.get_open_rate(),
            'click_rate': campaign.get_click_rate(),
            'bounce_rate': campaign.get_bounce_rate(),
            'unsubscribe_rate': campaign.get_unsubscribe_rate(),
            'sent_at': campaign.sent_at,
        })
    
    # ── Top Performing Campaigns ──────────────────────────────────────
    top_performers = Campaign.objects.filter(
        status=Campaign.Status.SENT,
        sent_count__gt=0
    ).order_by('-opened_count')[:5]
    
    top_performers_data = []
    for campaign in top_performers:
        top_performers_data.append({
            'id': campaign.id,
            'subject': campaign.subject,
            'open_rate': campaign.get_open_rate(),
            'click_rate': campaign.get_click_rate(),
        })
    
    # ── Subscriber Engagement ─────────────────────────────────────────
    subscriber_engagement = CampaignRecipient.objects.filter(
        campaign__status=Campaign.Status.SENT
    ).aggregate(
        total_sent=Count('id'),
        total_opened=Count('id', filter=Q(status=CampaignRecipient.Status.OPENED)),
        total_clicked=Count('id', filter=Q(status=CampaignRecipient.Status.CLICKED)),
        total_bounced=Count('id', filter=Q(status=CampaignRecipient.Status.BOUNCED)),
        total_unsubscribed=Count('id', filter=Q(status=CampaignRecipient.Status.UNSUBSCRIBED)),
        total_failed=Count('id', filter=Q(status=CampaignRecipient.Status.FAILED)),
    )
    
    # ── Click Link Analytics ──────────────────────────────────────────
    all_clicked_links = []
    for recipient in CampaignRecipient.objects.filter(
        campaign__status=Campaign.Status.SENT,
        clicked_links__isnull=False
    ).exclude(clicked_links=[]):
        if recipient.clicked_links:
            all_clicked_links.extend(recipient.clicked_links)
    
    from collections import Counter
    top_links = Counter(all_clicked_links).most_common(10)
    
    # ── Daily Trends Data (for charts) ────────────────────────────────
    daily_labels = [item['date'].strftime('%b %d') for item in daily_stats]
    daily_opens = [item['opens'] for item in daily_stats]
    daily_clicks = [item['clicks'] for item in daily_stats]
    daily_sent = [item['sent'] for item in daily_stats]
    
    # ── Recent Tracking Events ────────────────────────────────────────
    recent_tracking = EmailTracking.objects.select_related(
        'campaign', 'recipient__subscriber'
    ).order_by('-created_at')[:50]
    
    # ── Weekly Summary ─────────────────────────────────────────────────
    weekly_summary = Campaign.objects.filter(
        status=Campaign.Status.SENT
    ).annotate(
        week=TruncMonth('sent_at')
    ).values('week').annotate(
        total_sent=Sum('sent_count'),
        total_opens=Sum('opened_count'),
        total_clicks=Sum('clicked_count'),
        campaigns=Count('id')
    ).order_by('-week')[:12]
    
    # ── Campaign Stats Summary ────────────────────────────────────────
    campaign_stats_summary = {
        'total_campaigns': total_campaigns,
        'sent_campaigns': sent_campaigns,
        'draft_campaigns': draft_campaigns,
        'failed_campaigns': failed_campaigns,
        'scheduled_campaigns': scheduled_campaigns,
        'total_sent': total_sent,
        'total_recipients': total_recipients,
        'total_opens': total_opens,
        'total_clicks': total_clicks,
        'total_bounced': total_bounced,
        'total_unsubscribed': total_unsubscribed,
        'overall_open_rate': overall_open_rate,
        'overall_click_rate': overall_click_rate,
        'overall_bounce_rate': overall_bounce_rate,
        'overall_unsubscribe_rate': overall_unsubscribe_rate,
    }
    
    # ── Engagement Breakdown ──────────────────────────────────────────
    engagement_breakdown = {
        'opened': subscriber_engagement['total_opened'],
        'clicked': subscriber_engagement['total_clicked'],
        'bounced': subscriber_engagement['total_bounced'],
        'unsubscribed': subscriber_engagement['total_unsubscribed'],
        'failed': subscriber_engagement['total_failed'],
        'not_opened': subscriber_engagement['total_sent'] - subscriber_engagement['total_opened'],
    }
    
    context = {
        # Campaign stats
        'campaign_stats': campaign_stats_summary,
        'campaign_performance': campaign_performance,
        'top_performers': top_performers_data,
        
        # Engagement data
        'engagement_breakdown': engagement_breakdown,
        'subscriber_engagement': subscriber_engagement,
        
        # Chart data
        'daily_labels': json.dumps(daily_labels),
        'daily_opens': json.dumps(daily_opens),
        'daily_clicks': json.dumps(daily_clicks),
        'daily_sent': json.dumps(daily_sent),
        'weekly_summary': weekly_summary,
        
        # Recent activity
        'recent_tracking': recent_tracking,
        'top_links': top_links,
        
        # All campaigns
        'campaigns': recent_campaigns[:50],
        
        # Sidebar counts
        'draft_count': Campaign.objects.filter(status=Campaign.Status.DRAFT).count(),
        'new_message_count': ContactMessage.objects.filter(status='new').count(),
        'title': 'Campaign Analytics · Dashboard',
    }
    return render(request, 'pages/tracking_stats.html', context)

def custom_logout(request):
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('/')