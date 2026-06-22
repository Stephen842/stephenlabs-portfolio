from django import forms
from django import forms
from tinymce.widgets import TinyMCE
from django.utils.text import slugify
import re
from tinymce.widgets import TinyMCE

from lab.models import Campaign, CampaignTemplate, EmailSegment
from blog.models import Post, Category, Tag


class CustomClearableFileInput(forms.ClearableFileInput):
    '''Custom file input that hides the default 'Currently' text and 'Clear' checkbox'''

    template_name = 'pages/custom_clearable_file_input.html'

    def __init__(self, attrs=None):
        default_attrs = {
            'class': 'field-input',
            'accept': 'image/jpeg,image/png,image/gif,image/webp',
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)


class CategoryForm(forms.ModelForm):
    '''Form for creating and editing categories'''
    class Meta:
        model = Category
        fields = ['name', 'slug']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'field-input',
                'placeholder': 'e.g., Python Programming'
            }),
            'slug': forms.TextInput(attrs={
                'class': 'field-input',
                'placeholder': 'e.g., python-programming'
            }),
        }

    def clean_slug(self):
        slug = self.cleaned_data.get('slug')
        if slug:
            slug = re.sub(r'[^a-z0-9-]', '-', slug.lower())
            slug = re.sub(r'-+', '-', slug).strip('-')
        return slug


class TagForm(forms.ModelForm):
    '''Form for creating and editing tags'''
    class Meta:
        model = Tag
        fields = ['name', 'slug']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'field-input',
                'placeholder': 'e.g., Django'
            }),
            'slug': forms.TextInput(attrs={
                'class': 'field-input',
                'placeholder': 'e.g., django'
            }),
        }

    def clean_slug(self):
        slug = self.cleaned_data.get('slug')
        if slug:
            slug = re.sub(r'[^a-z0-9-]', '-', slug.lower())
            slug = re.sub(r'-+', '-', slug).strip('-')
        return slug


class PostForm(forms.ModelForm):
    '''Form for creating and editing blog posts'''

    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'tag-checkbox-list',
        }),
    )

    new_tags_input = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'field-input',
            'placeholder': 'Add new tags, comma separated (optional)'
        }),
        help_text='Creates new tags not in the list above.'
    )

    class Meta:
        model = Post
        fields = ['title', 'slug', 'category', 'excerpt', 'content', 'featured_image', 'status']

        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'field-input',
                'placeholder': 'Enter post title',
                'id': 'post-title'
            }),
            'slug': forms.TextInput(attrs={
                'class': 'field-input',
                'placeholder': 'auto-generated-from-title',
                'id': 'post-slug'
            }),
            'category': forms.Select(attrs={
                'class': 'field-select',
                'id': 'post-category'
            }),
            'excerpt': forms.Textarea(attrs={
                'class': 'field-textarea',
                'rows': 3,
                'placeholder': 'A short summary of the post...',
                'id': 'post-excerpt'
            }),
            'content': TinyMCE(attrs={
                'class': 'field-textarea editor tinymce-editor',
                'id': 'post-content',
                'style': 'width:100%; min-height:500px;'
            }),

            'featured_image': CustomClearableFileInput(),
            'status': forms.Select(attrs={
                'class': 'field-select',
                'id': 'post-status'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['tags'].initial = self.instance.tags.all()

    def clean_slug(self):
        slug = self.cleaned_data.get('slug')
        if not slug:
            slug = slugify(self.cleaned_data.get('title', ''))
        return slug

    def save_tags(self, instance):
        '''
        Apply selected checkbox tags + any newly typed tag names to a
        saved Post instance. Call this AFTER instance.save() — m2m
        relations require the instance to already have a primary key.
        '''
        selected_tags = list(self.cleaned_data.get('tags', []))

        new_tags_input = self.cleaned_data.get('new_tags_input', '')
        if new_tags_input:
            for name in [n.strip().lower() for n in new_tags_input.split(',') if n.strip()]:
                slug = re.sub(r'-+', '-', re.sub(r'[^a-z0-9-]', '-', name)).strip('-')
                tag, _ = Tag.objects.get_or_create(name=name, defaults={'slug': slug})
                selected_tags.append(tag)
        instance.tags.set(selected_tags)
        return instance


class CampaignForm(forms.ModelForm):
    """Form for creating and editing campaigns"""
    
    class Meta:
        model = Campaign
        fields = [
            'subject', 'body', 'from_email', 'from_name', 'reply_to',
            'target_segments', 'target_tags', 'scheduled_at', 'priority',
            'tags', 'is_test', 'test_emails'
        ]
        widgets = {
            'subject': forms.TextInput(attrs={
                'class': 'field-input',
                'placeholder': 'Enter campaign subject line...'
            }),
            'body': TinyMCE(attrs={
                'class': 'field-textarea editor',
                'style': 'width:100%; min-height:400px;'
            }),
            'from_email': forms.EmailInput(attrs={
                'class': 'field-input',
                'placeholder': 'Stephenslab001@gmail.com'
            }),
            'from_name': forms.TextInput(attrs={
                'class': 'field-input',
                'placeholder': 'The StephensLab Team'
            }),
            'reply_to': forms.EmailInput(attrs={
                'class': 'field-input',
                'placeholder': 'Stephenslab001@gmail.com'
            }),
            'target_segments': forms.SelectMultiple(attrs={
                'class': 'field-select'
            }),
            'target_tags': forms.TextInput(attrs={
                'class': 'field-input',
                'placeholder': 'tag1, tag2, tag3'
            }),
            'scheduled_at': forms.DateTimeInput(attrs={
                'class': 'field-input',
                'type': 'datetime-local'
            }),
            'priority': forms.Select(attrs={
                'class': 'field-select'
            }),
            'tags': forms.TextInput(attrs={
                'class': 'field-input',
                'placeholder': 'campaign-tag1, campaign-tag2'
            }),
            'test_emails': forms.TextInput(attrs={
                'class': 'field-input',
                'placeholder': 'test1@example.com, test2@example.com'
            }),
        }
        widgets['is_test'] = forms.CheckboxInput(attrs={
            'class': 'field-checkbox'
        })
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['target_segments'].queryset = EmailSegment.objects.all()
        self.fields['target_segments'].required = False
        self.fields['target_segments'].help_text = 'Select subscriber segments to target'


class CampaignTemplateForm(forms.ModelForm):
    """Form for creating and editing campaign templates"""
    
    class Meta:
        model = CampaignTemplate
        fields = ['name', 'subject', 'body', 'description', 'category', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'field-input',
                'placeholder': 'Welcome Series - Email 1'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'field-input',
                'placeholder': 'Welcome to StephensLab!'
            }),
            'body': TinyMCE(attrs={
                'class': 'field-textarea editor',
                'style': 'width:100%; min-height:400px;'
            }),
            'description': forms.Textarea(attrs={
                'class': 'field-textarea',
                'rows': 3,
                'placeholder': 'Describe when to use this template...'
            }),
            'category': forms.TextInput(attrs={
                'class': 'field-input',
                'placeholder': 'Welcome, Newsletter, Promotional, etc.'
            }),
        }


class SendTestEmailForm(forms.Form):
    """Form for sending test emails"""
    
    test_email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'field-input',
            'placeholder': 'test@example.com'
        })
    )
    subject = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'field-input',
            'placeholder': 'Test: Subject line'
        })
    )
    body = forms.CharField(
        widget=TinyMCE(attrs={
            'class': 'field-textarea editor',
            'style': 'width:100%; min-height:300px;'
        })
    )