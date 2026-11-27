from django.conf import settings
from django.contrib.auth import get_user_model


def navigation(request):
    user = request.user
    context = {
        'turnstile_site_key': settings.TURNSTILE_SITE_KEY,
        'show_app_shell': user.is_authenticated and (user.is_staff or (user.is_approved and user.has_complete_profile)),
    }
    if context['show_app_shell'] and user.is_staff:
        context['pending_count'] = get_user_model().objects \
            .filter(is_approved=False, is_staff=False, is_active=True, emailaddress__verified=True) \
            .count()
    return context
