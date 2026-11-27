from django.conf import settings
from django.contrib.auth import get_user_model


def navigation(request):
    """Picks the layout for pages that both approved and not yet approved users see (profile, allauth)."""
    user = request.user
    has_app_access = user.is_authenticated and (user.is_staff or (user.is_approved and user.has_complete_profile))
    context = {
        'layout': 'layouts/app.html' if has_app_access else 'layouts/entrance.html',
        'turnstile_site_key': settings.TURNSTILE_SITE_KEY,
    }
    if has_app_access and user.is_staff:
        context['pending_count'] = get_user_model().objects.waiting_for_approval().count()
    return context
