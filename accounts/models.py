import secrets

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        return self.create_user(
            email,
            password,
            is_staff=True,
            is_superuser=True,
            is_approved=True,
            **extra_fields,
        )

    def waiting_for_approval(self):
        return self \
            .filter(is_approved=False, is_staff=False, is_active=True, emailaddress__verified=True) \
            .order_by('date_joined')


AVATAR_COLORS = ['#1164a3', '#e01e5a', '#2bac76', '#8a3ffc', '#d97706', '#0f766e', '#b45309']


def random_photo_path(user, filename):
    return f'photos/{secrets.token_urlsafe(16)}.webp'


class User(AbstractUser):
    LANGUAGE_CHOICES = [
        ('cs', 'Čeština'),
        ('en', 'English'),
    ]

    username = None
    email = models.EmailField(_('email'), unique=True)
    birth_year = models.PositiveSmallIntegerField(_('year of birth'), null=True, blank=True)
    hometown = models.CharField(_('where I am from'), max_length=100, blank=True)
    job = models.CharField(_('job'), max_length=100, blank=True)
    hobbies = models.CharField(_('hobbies'), max_length=300, blank=True)
    photo = models.ImageField(_('photo'), upload_to=random_photo_path, blank=True)
    language = models.CharField(_('language'), max_length=2, choices=LANGUAGE_CHOICES, default='cs')
    is_approved = models.BooleanField(_('approved'), default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        ordering = ['first_name', 'last_name']

    def __str__(self):
        return self.get_full_name() or self.email

    @property
    def initials(self):
        return ''.join(part[0] for part in str(self).split()[:2]).upper()

    @property
    def avatar_color(self):
        return AVATAR_COLORS[self.id % len(AVATAR_COLORS)]

    @property
    def has_complete_profile(self):
        return bool(self.first_name and self.last_name and self.birth_year)

    @property
    def has_app_access(self):
        return self.is_staff or (self.is_approved and self.has_complete_profile)
