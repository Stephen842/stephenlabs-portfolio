from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from tinymce.models import HTMLField

from blog.models import Subscriber

class Campaign(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        SCHEDULED = 'scheduled', 'Scheduled'
        SENDING = 'sending', 'Sending'
        SENT = 'sent', 'Sent'
        FAILED = 'failed', 'Failed'
    
    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        NORMAL = 'normal', 'Normal'
        HIGH = 'high', 'High'
        URGENT = 'urgent', 'Urgent'
    
    # Campaign details
    subject = models.CharField(max_length=255)
    body = HTMLField()
    from_email = models.EmailField(default='Stephenslab001@gmail.com')
    from_name = models.CharField(max_length=255, default='The StephensLab Team')
    reply_to = models.EmailField(default='Stephenslab001@gmail.com')
    
    # Targeting
    target_segments = models.JSONField(default=list, blank=True, null=True, help_text='List of subscriber segments to target')
    target_tags = models.JSONField(default=list, blank=True, null=True, help_text='List of tags to target')
    
    # Scheduling
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    # Tracking
    total_recipients = models.IntegerField(default=0)
    sent_count = models.IntegerField(default=0)
    opened_count = models.IntegerField(default=0)
    clicked_count = models.IntegerField(default=0)
    bounced_count = models.IntegerField(default=0)
    unsubscribe_count = models.IntegerField(default=0)
    
    # Priority and metadata
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL)
    tags = models.JSONField(default=list, blank=True)
    is_test = models.BooleanField(default=False)
    test_emails = models.JSONField(default=list, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='campaigns'
    )
    
    def __str__(self):
        return self.subject
    
    def get_recipient_count(self):
        """Get the number of recipients for this campaign"""
        return self.total_recipients
    
    def get_open_rate(self):
        """Calculate open rate"""
        if self.sent_count == 0:
            return 0
        return (self.opened_count / self.sent_count) * 100
    
    def get_click_rate(self):
        """Calculate click rate"""
        if self.sent_count == 0:
            return 0
        return (self.clicked_count / self.sent_count) * 100
    
    def get_bounce_rate(self):
        """Calculate bounce rate"""
        if self.sent_count == 0:
            return 0
        return (self.bounced_count / self.sent_count) * 100
    
    def get_unsubscribe_rate(self):
        """Calculate unsubscribe rate"""
        if self.sent_count == 0:
            return 0
        return (self.unsubscribe_count / self.sent_count) * 100
    
    class Meta:
        ordering = ['-created_at']


class CampaignRecipient(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SENT = 'sent', 'Sent'
        OPENED = 'opened', 'Opened'
        CLICKED = 'clicked', 'Clicked'
        BOUNCED = 'bounced', 'Bounced'
        UNSUBSCRIBED = 'unsubscribed', 'Unsubscribed'
        FAILED = 'failed', 'Failed'
    
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='recipients')
    subscriber = models.ForeignKey(Subscriber, on_delete=models.CASCADE, related_name='campaign_recipients')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    sent_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    clicked_links = models.JSONField(default=list, blank=True)
    error_message = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.campaign.subject} → {self.subscriber.email}"
    
    class Meta:
        unique_together = ['campaign', 'subscriber']
        ordering = ['-sent_at']


class CampaignTemplate(models.Model):
    name = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    body = HTMLField()
    description = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='campaign_templates'
    )
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']


class EmailTracking(models.Model):
    class EventType(models.TextChoices):
        OPEN = 'open', 'Open'
        CLICK = 'click', 'Click'
        BOUNCE = 'bounce', 'Bounce'
        UNSUBSCRIBE = 'unsubscribe', 'Unsubscribe'
        COMPLAINT = 'complaint', 'Complaint'
    
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='tracking_events')
    recipient = models.ForeignKey(CampaignRecipient, on_delete=models.CASCADE, related_name='tracking_events')
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    url = models.URLField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    def __str__(self):
        return f"{self.campaign.subject} - {self.event_type} - {self.created_at}"
    
    class Meta:
        ordering = ['-created_at']


class EmailSegment(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    filter_conditions = models.JSONField(default=dict)
    subscriber_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    def update_count(self):
        """Update the subscriber count for this segment"""
        # This would be implemented based on your filter conditions
        # For now, we'll just set it to 0 and let the admin calculate
        self.save(update_fields=['subscriber_count'])
    
    class Meta:
        ordering = ['name']


class CampaignAnalytics(models.Model):
    campaign = models.OneToOneField(Campaign, on_delete=models.CASCADE, related_name='analytics')
    total_opens = models.IntegerField(default=0)
    total_clicks = models.IntegerField(default=0)
    unique_opens = models.IntegerField(default=0)
    unique_clicks = models.IntegerField(default=0)
    conversions = models.IntegerField(default=0)
    revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    conversion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    avg_time_to_open = models.DurationField(null=True, blank=True)
    avg_time_to_click = models.DurationField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Analytics for {self.campaign.subject}"


class SiteStats(models.Model):
    visit_count = models.IntegerField(default=0)
    subscribers_count = models.IntegerField(default=0)
    posts_published = models.IntegerField(default=0)
    campaigns_sent = models.IntegerField(default=0)
    total_opens = models.IntegerField(default=0)
    total_clicks = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def increment_visit(self):
        self.visit_count += 1
        self.save(update_fields=['visit_count'])
        return self.visit_count
    
    def increment_subscribers(self):
        self.subscribers_count += 1
        self.save(update_fields=['subscribers_count'])
        return self.subscribers_count
    
    def increment_campaigns_sent(self):
        self.campaigns_sent += 1
        self.save(update_fields=['campaigns_sent'])
        return self.campaigns_sent
    
    def increment_opens(self, count=1):
        self.total_opens += count
        self.save(update_fields=['total_opens'])
        return self.total_opens
    
    def increment_clicks(self, count=1):
        self.total_clicks += count
        self.save(update_fields=['total_clicks'])
        return self.total_clicks