from django.conf import settings
from django.shortcuts import redirect
from django.utils import translation


class UserLanguageMiddleware:
    """Activates the language the user picked, never the one the browser asks for."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
        if request.user.is_authenticated:
            language = request.user.language
        if language not in dict(settings.LANGUAGES):
            language = settings.LANGUAGE_CODE
        translation.activate(language)
        request.LANGUAGE_CODE = language
        response = self.get_response(request)
        response.headers.setdefault('Content-Language', language)
        return response


# Paths a signed-in user may open before their profile is complete and an admin has approved them.
OPEN_PATH_PREFIXES = (
    '/accounts/',
    '/profile/',
    '/pending/',
    '/language/',
    '/admin/',
    settings.MEDIA_URL,
    '/' + settings.STATIC_URL,
)


class ApprovedUserMiddleware:
    """Keeps signed-in users on their profile until it is complete, then on a waiting page until approved."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        if (
            user.is_authenticated and
            not user.is_staff and
            not request.path.startswith(OPEN_PATH_PREFIXES)
        ):
            if not user.has_complete_profile:
                return redirect('profile')
            if not user.is_approved:
                return redirect('pending')
        return self.get_response(request)
