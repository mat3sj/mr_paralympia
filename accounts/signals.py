from allauth.account.signals import user_signed_up
from django.core.mail import mail_admins
from django.dispatch import receiver
from django.urls import reverse


@receiver(user_signed_up)
def notify_admins_about_signup(request, user, **kwargs):
    approval_url = request.build_absolute_uri(reverse('manage_participants'))
    mail_admins(
        f'New registration: {user.email}',
        f'{user.email} signed up and waits for approval.\n\n{approval_url}',
    )
