from django.db.models import Q
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.conf import settings
from .models import Post, Subscriber


def filter_posts(request, queryset=None):
    '''
    Reusable blog post filtering logic.
    Can be used in views, CBVs, APIs, etc.
    '''

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


def subscribe_email(request, email):
    '''
    Subscribe a user to the newsletter and send a confirmation email.
    Returns True if subscription is successful, False otherwise.
    '''
    if not email:
        return False

    # Create or update subscriber
    subscriber, created_at = Subscriber.objects.get_or_create(
        email=email,
        defaults={'is_active': True}
    )

    if not subscriber.is_active:
        subscriber.is_active = True
        subscriber.save()

    # Build unsubscribe URL
    unsubscribe_url = request.build_absolute_uri(
        reverse('unsubscribe', args=[subscriber.id])
    )

    homepage_url = request.build_absolute_uri(
        reverse('post_list')
    )

    # Prepare email content using templates
    context = {
        'unsubscribe_url': unsubscribe_url,
        'homepage_url': homepage_url,
        'subscriber_email': subscriber.email
    }

    subject = 'Welcome to StephenLabs Newsletter'
    from_email = settings.DEFAULT_FROM_EMAIL
    to = [subscriber.email]

    html_content = render_to_string('pages/newsletter.html', context)
    text_content = "Thank you for subscribing to StephenLabs."

    # Send email
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=from_email,
        to=to,
    )
    msg.attach_alternative(html_content, 'text/html')
    msg.send(fail_silently=False)

    return True