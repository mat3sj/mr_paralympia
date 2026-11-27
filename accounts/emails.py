from django.core.mail import send_mail
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext as _


def send_approval_email(request, user):
    with translation.override(user.language):
        send_mail(
            _('Mr. Paralympia: your account is approved'),
            _('An admin approved your account. Sign in here: %(url)s') % {
                'url': request.build_absolute_uri(reverse('home')),
            },
            None,
            [user.email],
        )
