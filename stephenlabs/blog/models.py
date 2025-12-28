from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.utils import timezone
import math
from django_ckeditor_5.fields import CKEditor5Field


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
    

class Post(models.Model):

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'
    
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=270, unique=True)
    excerpt = models.TextField(help_text='Short summary shown on blog listing pages')
    content = CKEditor5Field('Content', config_name='default')
    featured_image = models.ImageField(upload_to='blog/images/', blank=True, null=True)
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
        words = len(self.content.split())
        self.reading_time = math.ceil(words / 100) # 100 words per minutes

        super().save(*args, **kwargs)
