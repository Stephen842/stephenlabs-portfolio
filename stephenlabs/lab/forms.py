from django import forms
from blog.models import Post, Category, Tag
from django.utils.text import slugify
import re


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
    """Form for creating and editing blog posts"""
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
            'content': forms.Textarea(attrs={
                'class': 'field-textarea',
                'rows': 20,
                'placeholder': 'Write your post content here...',
                'id': 'post-content'
            }),
            'featured_image': forms.ClearableFileInput(attrs={
                'class': 'field-input',
                'id': 'id_featured_image',
                'accept': 'image/jpeg,image/png,image/gif,image/webp',
            }),
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

    def save(self, commit=True):
        instance = super().save(commit=False)

        if commit:
            instance.save()
            self.save_m2m()  # saves self.fields['tags'] (the checkbox selections)

            # Merge in any newly typed tags alongside the checked ones
            new_tags_input = self.cleaned_data.get('new_tags_input', '')
            if new_tags_input:
                tag_names = [name.strip().lower() for name in new_tags_input.split(',') if name.strip()]
                new_tags = []
                for name in tag_names:
                    slug = re.sub(r'[^a-z0-9-]', '-', name)
                    slug = re.sub(r'-+', '-', slug).strip('-')
                    tag, _ = Tag.objects.get_or_create(name=name, defaults={'slug': slug})
                    new_tags.append(tag)
                if new_tags:
                    instance.tags.add(*new_tags)

        return instance