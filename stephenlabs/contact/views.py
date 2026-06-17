from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from django.conf import settings
from django.db.models import Q
from django.urls import reverse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.template.loader import render_to_string


from contact.models import ContactMessage, ContactSetting, ContactAttempt
from contact.forms import ContactForm, ContactReplyForm

from blog.models import Post, Category, Tag
from blog.utils import filter_posts, subscribe_email

import logging
logger = logging.getLogger(__name__)


def get_client_ip(request):
    '''Get client IP address from request'''
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def check_rate_limit(ip_address, email):
    '''Check if the user has exceeded rate limits'''
    try:
        settings_obj = ContactSetting.objects.first()
        if not settings_obj or not settings_obj.enable_rate_limiting:
            return True  # No rate limiting enabled
        
        window_hours = settings_obj.rate_limit_window_hours
        max_messages = settings_obj.rate_limit_per_ip
        
        cutoff_time = timezone.now() - timezone.timedelta(hours=window_hours)
        
        # Check IP-based rate limit
        ip_count = ContactAttempt.objects.filter(
            ip_address=ip_address,
            attempted_at__gte=cutoff_time,
            was_successful=True
        ).count()
        
        if ip_count >= max_messages:
            return False
        
        # Check email-based rate limit (stricter: max 2 per email per day)
        email_cutoff = timezone.now() - timezone.timedelta(days=1)
        email_count = ContactAttempt.objects.filter(
            email=email,
            attempted_at__gte=email_cutoff,
            was_successful=True
        ).count()
        
        if email_count >= 3:
            return False
        
        return True
    except Exception:
        return True  # Default to allow if settings not found


def send_auto_reply(contact_message):
    '''Send automatic HTML reply to user using email standard'''
    try:
        settings_obj = ContactSetting.objects.first()
        if not settings_obj or not settings_obj.auto_reply_enabled:
            logger.warning("Auto-reply disabled in settings")
            return
        
        context = {
            'name': contact_message.name,
            'id': contact_message.id,
            'homepage_url': settings.SITE_URL,
            'privacy_policy_url': f"{settings.SITE_URL}/privacy-policy/",
        }
        
        html_content = render_to_string('pages/contact_auto_reply_email.html', context)
        text_content = render_to_string('pages/contact_auto_reply_email.txt', context)

        logger.info(f"Rendered email templates for {contact_message.email}")
        
        email = EmailMultiAlternatives(
            subject=f"Thank you for contacting StephensLab",
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[contact_message.email],
            reply_to=['ugotachisomstephen@gmail.com'],
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)

        logger.info(f"Auto-reply sent successfully to {contact_message.email}")
        
    except Exception as e:
        logger.error(f'Auto-reply failed: {e}', exc_info=True)
        #print(f'Auto-reply failed: {e}')


def send_admin_notification(contact_message):
    '''Send HTML email notification to admin using email standard'''
    try:
        settings_obj = ContactSetting.objects.first()
        if not settings_obj or not settings_obj.send_email_notification:
            logger.warning("Admin notification disabled in settings")
            return
        
        admin_email = settings_obj.contact_email or settings.DEFAULT_FROM_EMAIL
        
        context = {
            'name': contact_message.name,
            'email': contact_message.email,
            'category': contact_message.get_subject_category_display(),
            'subject': contact_message.subject,
            'message': contact_message.message,
            'ip_address': contact_message.ip_address,
            'received_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC'),
            'admin_url': f"{settings.SITE_URL}{reverse('admin:contact_contactmessage_change', args=[contact_message.id])}",
            'homepage_url': settings.SITE_URL,
        }
        
        html_content = render_to_string('pages/admin_notification_email.html', context)
        text_content = render_to_string('pages/admin_notification_email.txt', context)

        logger.info(f"Rendered admin templates for message #{contact_message.id}")
        
        subject = f'[StephensLab] New contact message from {contact_message.name}'
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[admin_email],
            reply_to=[contact_message.email],
        )
        email.attach_alternative(html_content, "text/html")
        
        if settings_obj.contact_email_cc:
            email.cc = [settings_obj.contact_email_cc]
        
        email.send(fail_silently=False)

        logger.info(f"Admin notification sent to {admin_email}")
        
    except Exception as e:
        #print(f'Admin notification failed: {e}')
        logger.error(f'Admin notification failed: {e}', exc_info=True)


@csrf_protect
def contact_view(request):
    '''Public contact page view'''
    
    # Get or create settings
    settings_obj, created = ContactSetting.objects.get_or_create(
        id=1,
        defaults={'contact_email': 'ugotachisomstephen@gmail.com'}
    )
    
    # Get client information
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    referrer = request.META.get('HTTP_REFERER', None)
    
    # Handle Newsletter Subscription (footer form)
    if request.method == 'POST' and 'footer_email' in request.POST:
        email = request.POST.get('footer_email')
        # Call subscribe function (make sure it exists)
        from blog.utils import subscribe_email  # or wherever your function is
        subscribe_email(request, email)
        messages.success(request, "Thank you! You've successfully subscribed to the StephensLab newsletter.")
        return redirect('contact:contact')
    
    # Handle Contact Form
    if request.method == 'POST':
        form = ContactForm(request.POST)
        
        # Check honeypot
        if request.POST.get('website', ''):
            messages.error(request, 'Spam detected. Your message was not sent.')
            return redirect('contact:contact')
        
        # Check rate limit
        email = request.POST.get('email', '')
        if not check_rate_limit(ip_address, email):
            messages.error(
                request, 
                'You have sent too many messages. Please wait before sending another message.'
            )
            return redirect('contact:contact')
        
        if form.is_valid():
            # Save the contact message
            contact_message = form.save(commit=False)
            contact_message.ip_address = ip_address
            contact_message.user_agent = user_agent
            contact_message.referrer = referrer
            contact_message.save()
            
            # Record the attempt
            ContactAttempt.objects.create(
                ip_address=ip_address,
                email=email,
                attempted_at=timezone.now(),
                was_successful=True,
                user_agent=user_agent
            )
            
            # Send auto-reply to user
            send_auto_reply(contact_message)
            
            # Send notification to admin
            send_admin_notification(contact_message)
            
            messages.success(
                request, 
                "Thank you for reaching out! We'll respond to your message within 2-3 business days."
            )
            return redirect('contact:contact')
        else:
            # Record failed attempt
            ContactAttempt.objects.create(
                ip_address=ip_address,
                email=request.POST.get('email', ''),
                attempted_at=timezone.now(),
                was_successful=False,
                user_agent=user_agent
            )
    else:
        form = ContactForm()
    
    base_queryset = Post.objects.filter(
        status=Post.Status.PUBLISHED
    ).select_related('category', 'author').prefetch_related('tags')
    
    posts = filter_posts(request, base_queryset)
    
    context = {
        'form': form,
        'settings': settings_obj,
        'page_title': 'Contact StephensLab',
        'meta_description': 'Get in touch with StephensLab for technical inquiries, collaborations, or feedback.',
        
        # Blog sidebar context
        'posts': posts,
        'categories': Category.objects.all(),
        'tags': Tag.objects.all(),
        'selected_category': request.GET.get('category'),
        'selected_tag': request.GET.get('tag'),
        'query': request.GET.get('q'),
    }
    
    return render(request, 'pages/contact.html', context)

@staff_member_required
def contact_messages_list(request):
    '''Admin view for listing all contact messages'''
    
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    category_filter = request.GET.get('category', '')
    search_query = request.GET.get('q', '')
    
    # Base queryset
    messages_qs = ContactMessage.objects.all()

    # Calculate counts for all statuses (before any filters)
    total_count = messages_qs.count()
    new_count = messages_qs.filter(status='new').count()
    read_count = messages_qs.filter(status='read').count()
    replied_count = messages_qs.filter(status='replied').count()
    archived_count = messages_qs.filter(status='archived').count()
    spam_count = messages_qs.filter(status='spam').count()
    
    # Apply filters
    if status_filter:
        messages_qs = messages_qs.filter(status=status_filter)
    if category_filter:
        messages_qs = messages_qs.filter(subject_category=category_filter)
    if search_query:
        messages_qs = messages_qs.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(subject__icontains=search_query) |
            Q(message__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(messages_qs, 50)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'messages': page_obj,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'search_query': search_query,
        'status_choices': ContactMessage.STATUS_CHOICES,
        'category_choices': ContactMessage.SUBJECT_CHOICES,

        'total_count': total_count,
        'new_count': new_count,
        'read_count': read_count,
        'replied_count': replied_count,
        'archived_count': archived_count,
        'spam_count': spam_count,
    }
    
    return render(request, 'pages/admin_messages.html', context)


@staff_member_required
def contact_message_detail(request, message_id):
    '''Admin view for viewing and replying to a single contact message'''
    
    contact_message = get_object_or_404(ContactMessage, id=message_id)
    
    # Mark as read if it's new
    if contact_message.status == 'new':
        contact_message.mark_as_read()
    
    if request.method == 'POST':
        form = ContactReplyForm(request.POST)
        if form.is_valid():
            # Send reply email
            reply_subject = form.cleaned_data['reply_subject']
            reply_body = form.cleaned_data['reply_body']
            
            # Prepare context for the email template
            context = {
                'name': contact_message.name,
                'subject': reply_subject,
                'reply_body': reply_body,
                'homepage_url': getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000'),
                'privacy_policy_url': f"{getattr(settings, 'SITE_URL', 'http://127.0.0.1:8000')}/privacy-policy/",
            }
            
            # Render HTML and plain text templates
            html_content = render_to_string('pages/contact_reply_email.html', context)
            text_content = render_to_string('pages/contact_reply_email.txt', context)
            
            # Create email with both HTML and plain text versions
            email = EmailMultiAlternatives(
                subject=f'Re: {reply_subject}',
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[contact_message.email],
                reply_to=['ugotachisomstephen@gmail.com'],
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=False)
            
            # Update message status
            contact_message.mark_as_replied()
            
            # Save admin notes if provided
            admin_notes = request.POST.get('admin_notes', '')
            if admin_notes:
                contact_message.admin_notes = admin_notes
                contact_message.save(update_fields=['admin_notes'])
            
            messages.success(request, f'Reply sent to {contact_message.email}')
            return redirect('contact:contact_message_detail', message_id=message_id)
    else:
        form = ContactReplyForm(initial={
            'reply_subject': f'Re: {contact_message.subject}',
        })
    
    context = {
        'message': contact_message,
        'form': form,
    }
    
    return render(request, 'pages/admin_message_detail.html', context)



@staff_member_required
def contact_message_update_status(request, message_id):
    '''AJAX endpoint for updating message status'''
    
    if request.method == 'POST':
        contact_message = get_object_or_404(ContactMessage, id=message_id)
        new_status = request.POST.get('status')
        
        if new_status in dict(ContactMessage.STATUS_CHOICES):
            contact_message.status = new_status
            contact_message.save(update_fields=['status', 'updated_at'])
            
            return JsonResponse({'success': True, 'status': new_status})
    
    return JsonResponse({'success': False}, status=400)


@staff_member_required
def contact_message_delete(request, message_id):
    '''Admin view for deleting contact messages'''
    
    contact_message = get_object_or_404(ContactMessage, id=message_id)
    
    if request.method == 'POST':
        contact_message.delete()
        messages.success(request, 'Message deleted successfully.')
        return redirect('contact:contact_messages_list')
    
    return render(request, 'pages/admin_confirm_delete.html', {'message': contact_message})


@require_http_methods(['POST'])
def contact_health_check(request):
    '''Simple health check endpoint for contact system'''
    
    return JsonResponse({
        'status': 'ok',
        'timestamp': timezone.now().isoformat(),
    })


def testing(request):
    return render(request, 'pages/contact_reply_email.html')
