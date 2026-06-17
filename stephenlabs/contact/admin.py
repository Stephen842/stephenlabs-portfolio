from django.contrib import admin
from .models import ContactMessage, ContactSetting, ContactAttempt

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'email', 'subject_category', 'status', 'created_at']
    list_filter = ['status', 'subject_category', 'created_at']
    search_fields = ['name', 'email', 'subject', 'message']
    readonly_fields = ['created_at', 'ip_address', 'user_agent']
    actions = ['mark_as_read', 'mark_as_replied']
    
    def mark_as_read(self, request, queryset):
        queryset.update(status='read')
    mark_as_read.short_description = "Mark selected messages as read"
    
    def mark_as_replied(self, request, queryset):
        queryset.update(status='replied')
    mark_as_replied.short_description = "Mark selected messages as replied"

@admin.register(ContactSetting)
class ContactSettingAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not ContactSetting.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(ContactAttempt)
class ContactAttemptAdmin(admin.ModelAdmin):
    list_display = ['ip_address', 'email', 'attempted_at', 'was_successful']
    list_filter = ['was_successful', 'attempted_at']
    search_fields = ['ip_address', 'email']