from django.contrib.auth import get_user_model


def app_access(request):
    """Picks the layout for pages that both approved and not yet approved users see (profile, allauth)."""
    user = request.user
    has_app_access = user.is_authenticated and user.has_app_access
    context = {'layout': 'layouts/app.html' if has_app_access else 'layouts/entrance.html'}
    if has_app_access and user.is_staff:
        context['waiting_for_approval_count'] = get_user_model().objects.waiting_for_approval().count()
    return context
