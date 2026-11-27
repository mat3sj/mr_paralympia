import io
import json
import urllib.parse
import urllib.request

from allauth.account.forms import SignupForm as AllauthSignupForm
from django import forms
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from PIL import Image, ImageOps

from accounts.models import User

TURNSTILE_VERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'


def is_turnstile_token_valid(token):
    payload = urllib.parse.urlencode({
        'secret': settings.TURNSTILE_SECRET_KEY,
        'response': token,
    }).encode()
    with urllib.request.urlopen(TURNSTILE_VERIFY_URL, payload, timeout=10) as response:
        return json.load(response)['success']


class SignupForm(AllauthSignupForm):
    def clean(self):
        cleaned_data = super().clean()
        if settings.TURNSTILE_SECRET_KEY:
            token = self.data.get('cf-turnstile-response', '')
            if not token or not is_turnstile_token_valid(token):
                raise forms.ValidationError(_('The anti-bot check failed. Reload the page and try again.'))
        return cleaned_data


PHOTO_SIZE = (400, 400)


def shrink_photo(uploaded_file):
    """Rotates by EXIF, crops to a square and stores a small WEBP whatever size the upload was."""
    image = ImageOps.exif_transpose(Image.open(uploaded_file))
    image = ImageOps.fit(image.convert('RGB'), PHOTO_SIZE, Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, 'WEBP', quality=85)
    return ContentFile(buffer.getvalue(), name='photo.webp')


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['photo', 'first_name', 'last_name', 'birth_year', 'hometown', 'job', 'hobbies', 'language']
        widgets = {
            'photo': forms.FileInput(attrs={'accept': 'image/*'}),
            'birth_year': forms.NumberInput(attrs={'inputmode': 'numeric'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['first_name', 'last_name', 'birth_year']:
            self.fields[field_name].required = True

    def clean_birth_year(self):
        birth_year = self.cleaned_data['birth_year']
        if not 1900 <= birth_year <= timezone.localdate().year:
            raise forms.ValidationError(_('Enter a real year of birth.'))
        return birth_year

    def clean_photo(self):
        photo = self.cleaned_data['photo']
        if isinstance(photo, UploadedFile):
            return shrink_photo(photo)
        return photo

    def save(self):
        old_photo_name = self.initial['photo'].name
        user = super().save()
        if old_photo_name and old_photo_name != user.photo.name:
            user.photo.storage.delete(old_photo_name)
        return user
