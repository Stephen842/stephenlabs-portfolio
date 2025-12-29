from django.contrib import admin
from .models import Category, Tag, Post


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'category', 'author', 'published_at', 'created_at',)

    list_filter = ('status', 'category', 'tags', 'created_at', 'published_at',)

    search_fields = ('title', 'excerpt', 'content',)

    prepopulated_fields = {'slug': ('title',)}

    autocomplete_fields = ('tags', 'category')

    readonly_fields = ('reading_time', 'created_at', 'updated_at',)

    fieldsets = (
        ('Post Content', {
            'fields': ('title', 'slug', 'excerpt', 'content', 'featured_image')
        }),
        ('Classification', {
            'fields': ('category', 'tags', 'status')
        }),
        ('Publishing', {
            'fields': ('author', 'published_at', 'reading_time')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    ordering = ('-created_at',)

    def save_model(self, request, obj, form, change):
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)
