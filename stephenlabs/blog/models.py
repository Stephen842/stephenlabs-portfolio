from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils import timezone

import math
import os
import re as _re

from tinymce.models import HTMLField


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True)

    class Meta:
        verbose_name_plural = 'Tags'
        ordering = ['name']

    def __str__(self):
        return self.name
    

def post_image_path(instance, filename):
    """Generate a unique path for uploaded post images"""
    ext = filename.split('.')[-1]
    filename = f"{slugify(instance.title)}-{timezone.now().strftime('%Y%m%d%H%M%S')}.{ext}"
    return os.path.join('posts', filename)


class Post(models.Model):

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'
    
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=270, unique=True)
    excerpt = models.TextField(help_text='Short summary shown on blog listing pages')
    content = HTMLField()
    featured_image = models.ImageField(upload_to=post_image_path, blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='posts')
    tags = models.ManyToManyField(Tag, blank=True, related_name='posts')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='blog_posts')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(blank=True, null=True)
    reading_time = models.PositiveIntegerField(help_text='Estimated reading time in minutes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['status']),
            models.Index(fields=['published_at'])
        ]

    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        # Auto-generate slug if missing
        if not self.slug:
            self.slug = slugify(self.title)

        # Auto-set published timestamp
        if self.status == self.Status.PUBLISHED and not self.published_at:
            self.published_at = timezone.now()

        # Auto-calculate reading time
        raw_content = self.content or ''
        plain_text = _re.sub(r'<[^>]+>', ' ', raw_content)  # strip HTML tags
        words = len(plain_text.split())
        self.reading_time = max(1, math.ceil(words / 200))   # 200 wpm is standard

        super().save(*args, **kwargs)


class Subscriber(models.Model):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email