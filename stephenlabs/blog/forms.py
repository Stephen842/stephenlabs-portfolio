from django import forms
from .models import Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['title', 'excerpt', 'content', 'featured_image', 'category', 'tags','status']

        widgets = {
            'tags': forms.CheckboxSelectMultiple(),  # nicer UI for selecting multiple tags
            'status': forms.Select()
        }

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