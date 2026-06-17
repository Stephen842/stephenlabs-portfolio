from django.db import models
from django.utils import timezone

class ContactMessage(models.Model):
    '''Model for storing contact form submissions'''
    
    SUBJECT_CHOICES = [
        ('general', 'General Inquiry'),
        ('technical', 'Technical Question'),
        ('collaboration', 'Collaboration / Partnership'),
        ('content', 'Content Suggestion'),
        ('bug', 'Bug Report'),
        ('privacy', 'Privacy Concern'),
        ('other', 'Other'),
    ]
    
    STATUS_CHOICES = [
        ('new', 'New'),
        ('read', 'Read'),
        ('replied', 'Replied'),
        ('archived', 'Archived'),
        ('spam', 'Spam'),
    ]
    
    # Contact information
    name = models.CharField(max_length=200, verbose_name='Full Name')
    email = models.EmailField(verbose_name='Email Address')
    subject_category = models.CharField(
        max_length=20, 
        choices=SUBJECT_CHOICES, 
        default='general',
        verbose_name='Subject Category'
    )
    subject = models.CharField(max_length=300, verbose_name='Subject')
    message = models.TextField(verbose_name='Message')
    
    # Metadata
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    referrer = models.URLField(blank=True, null=True)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    admin_notes = models.TextField(blank=True, verbose_name='Admin Notes')
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    replied_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Contact Message'
        verbose_name_plural = 'Contact Messages'
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['email']),
        ]
    
    def __str__(self):
        return f'{self.name} - {self.subject[:50]}'
    
    def mark_as_read(self):
        if self.status == 'new':
            self.status = 'read'
            self.save(update_fields=['status', 'updated_at'])
    
    def mark_as_replied(self):
        self.status = 'replied'
        self.replied_at = timezone.now()
        self.save(update_fields=['status', 'replied_at', 'updated_at'])


class ContactSetting(models.Model):
    '''Model for managing contact page settings'''
    
    # Email settings
    contact_email = models.EmailField(default='ugotachisomstephen@gmail.com')
    contact_email_cc = models.EmailField(blank=True, null=True)
    
    # Rate limiting
    rate_limit_per_ip = models.PositiveIntegerField(default=5, help_text='Maximum messages per IP address per hour')
    rate_limit_window_hours = models.PositiveIntegerField(default=1, help_text='Rate limit window in hours')
    
    # Auto-reply settings
    auto_reply_enabled = models.BooleanField(default=True)
    auto_reply_subject = models.CharField(max_length=200, default='Thank you for contacting StephensLab')
    auto_reply_body = models.TextField(
        default='',
        blank=True,
        help_text='This field is deprecated. Email content is handled by templates.'
    )
    
    # Spam protection
    enable_honeypot = models.BooleanField(default=True)
    enable_rate_limiting = models.BooleanField(default=True)
    
    # Notification settings
    send_email_notification = models.BooleanField(default=True)
    send_slack_webhook = models.BooleanField(default=False)
    slack_webhook_url = models.URLField(blank=True, null=True)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Contact Setting'
        verbose_name_plural = 'Contact Settings'
    
    def __str__(self):
        return 'Contact Page Settings'


class ContactAttempt(models.Model):
    '''Model for tracking contact form attempts (rate limiting and spam prevention)'''
    
    ip_address = models.GenericIPAddressField()
    email = models.EmailField()
    attempted_at = models.DateTimeField(default=timezone.now)
    was_successful = models.BooleanField(default=False)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-attempted_at']
        indexes = [
            models.Index(fields=['ip_address', '-attempted_at']),
            models.Index(fields=['email', '-attempted_at']),
        ]
    
    def __str__(self):
        return f'{self.ip_address} - {self.attempted_at}'