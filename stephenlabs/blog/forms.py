from django import forms
from blog.models import Post, Subscriber
from blog.models import Post, Category, Tag
from django.utils.text import slugify


class PostForm(forms.ModelForm):
    tags_input = forms.CharField(required=False, help_text='Comma-separated tag names')

    class Meta:
        model = Post
        fields = ['title', 'slug', 'excerpt', 'content', 'featured_image', 'category', 'tags','status']

        widgets = {
            'tags': forms.CheckboxSelectMultiple(),  # nicer UI for selecting multiple tags
            'status': forms.Select()
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            tags = ', '.join([tag.name for tag in self.instance.tags.all()])
            self.fields['tags_input'].initial = tags

    def clean_title(self):
        title = self.cleaned_data.get('title')
        if len(title) < 5:
            raise forms.ValidationError("Title must be at least 5 characters long.")
        return title

    def clean_content(self):
        content = self.cleaned_data.get('content')
        if len(content.split()) < 50:
            raise forms.ValidationError("Content must be at least 50 words.")
        return content
    
    def clean_slug(self):
        slug = self.cleaned_data.get('slug')
        if not slug:
            slug = slugify(self.cleaned_data.get('title', ''))
        return slug
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            self.save_m2m()
            tags_input = self.cleaned_data.get('tags_input', '')
            if tags_input:
                tag_names = [name.strip().lower() for name in tags_input.split(',') if name.strip()]
                tags = []
                for name in tag_names:
                    tag, _ = Tag.objects.get_or_create(name=name)
                    tags.append(tag)
                instance.tags.set(tags)
            elif instance.pk:
                instance.tags.clear()
        return instance

class SubscriberForm(forms.ModelForm):
    class Meta:
        model = Subscriber
        fields = ['email']