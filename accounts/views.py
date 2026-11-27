from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from accounts.forms import ProfileForm


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, request.FILES or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, _('Profile saved.'))
        response = redirect('home' if request.user.is_approved else 'waiting_for_approval')
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, request.user.language, max_age=365 * 24 * 3600)
        return response
    return render(request, 'accounts/profile.html', {'form': form})


@login_required
def waiting_for_approval(request):
    if request.user.is_approved:
        return redirect('home')
    return render(request, 'accounts/waiting_for_approval.html')


@require_POST
def switch_language(request):
    language = request.POST['language']
    if language not in dict(settings.LANGUAGES):
        language = settings.LANGUAGE_CODE
    if request.user.is_authenticated:
        request.user.language = language
        request.user.save(update_fields=['language'])
    next_url = request.POST.get('next', '/')
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = '/'
    response = redirect(next_url)
    response.set_cookie(settings.LANGUAGE_COOKIE_NAME, language, max_age=365 * 24 * 3600)
    return response
