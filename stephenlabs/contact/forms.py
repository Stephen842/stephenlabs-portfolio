from django import forms
from django.core.validators import RegexValidator

from contact.models import ContactMessage


class ContactForm(forms.ModelForm):
    '''Contact form with validation and spam protection'''
    
    # Honeypot field for spam prevention
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'honeypot',
            'autocomplete': 'off',
            'tabindex': '-1',
            'aria-hidden': 'true'
        }),
        label=''
    )
    
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject_category', 'subject', 'message']
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'contact-input',
                'placeholder': 'Your full name',
                'required': True,
            }),
            'email': forms.EmailInput(attrs={
                'class': 'contact-input',
                'placeholder': 'your@email.com',
                'required': True,
            }),
            'subject_category': forms.Select(attrs={
                'class': 'contact-select',
            }),
            'subject': forms.TextInput(attrs={
                'class': 'contact-input',
                'placeholder': 'Brief summary of your inquiry',
                'required': True,
            }),
            'message': forms.Textarea(attrs={
                'class': 'contact-textarea',
                'placeholder': 'Please provide details about your inquiry...',
                'rows': 8,
                'required': True,
            }),
        }
    
    def clean_website(self):
        '''Honeypot validation - if this field is filled, it's likely spam'''
        website = self.cleaned_data.get('website')
        if website:
            raise forms.ValidationError('Spam detected. Please try again.')
        return website
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if len(name) < 2:
            raise forms.ValidationError('Please enter your full name.')
        if len(name) > 200:
            raise forms.ValidationError('Name is too long.')
        return name.strip()
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Additional email validation beyond Django's built-in
        if '@' not in email or '.' not in email.split('@')[1]:
            raise forms.ValidationError('Please enter a valid email address.')
        return email.lower()
    
    def clean_subject(self):
        subject = self.cleaned_data.get('subject')
        if len(subject) < 3:
            raise forms.ValidationError('Subject must be at least 3 characters.')
        if len(subject) > 300:
            raise forms.ValidationError('Subject is too long.')
        return subject.strip()
    
    def clean_message(self):
        message = self.cleaned_data.get('message')
        if len(message) < 10:
            raise forms.ValidationError('Message must be at least 10 characters.')
        if len(message) > 5000:
            raise forms.ValidationError('Message is too long. Please limit to 5000 characters.')
        return message.strip()


class ContactReplyForm(forms.Form):
    '''Form for admin to reply to contact messages'''
    
    reply_subject = forms.CharField(max_length=300, required=True)
    reply_body = forms.CharField(widget=forms.Textarea(attrs={'rows': 10}), required=True)
    send_copy_to_user = forms.BooleanField(required=False, initial=True)
    
    def clean_reply_body(self):
        body = self.cleaned_data.get('reply_body')
        if len(body) < 10:
            raise forms.ValidationError('Reply must be at least 10 characters.')
        return body