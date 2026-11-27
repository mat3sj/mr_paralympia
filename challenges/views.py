import datetime

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from challenges.forms import DayForm
from challenges.models import Challenge, Participant
from challenges.payments import payment_message, payment_qr_svg
from challenges.standings import compute_result, date_range


def get_paid_participant(challenge, user):
    participant = challenge.participant_for(user) if challenge else None
    return participant if participant and participant.has_paid else None


@login_required
def home(request):
    if get_paid_participant(Challenge.current(), request.user):
        return redirect('day')
    return redirect('join')


def pick_date(date_text, challenge, result):
    if not date_text:
        return result.last_date
    try:
        date = datetime.date.fromisoformat(date_text)
    except ValueError:
        raise Http404
    return min(max(date, challenge.start_date), result.last_date)


def day_context(result, form):
    challenge = result.challenge
    standing = form.standing
    date = form.date
    points = standing.points_on(date)
    minimum = challenge.minimum_points(date)
    exercise_id_2_points = {entry.exercise_id: entry.points for entry in standing.date_2_entries.get(date, [])}
    first_chip_date = max(challenge.start_date, result.today - datetime.timedelta(days=challenge.edit_days + 1))
    return {
        'challenge': challenge,
        'result': result,
        'standing': standing,
        'date': date,
        'day_number': challenge.day_number(date),
        'today': result.today,
        'is_editable': result.is_editable(date),
        'last_edit_date': challenge.last_edit_date(date),
        'form': form,
        'rows': [
            {
                'exercise': exercise,
                'field': form.field_for(exercise),
                'points': exercise_id_2_points.get(exercise.id, 0),
            }
            for exercise in form.exercises
        ],
        'chips': [
            {
                'date': chip_date,
                'is_locked': challenge.is_locked(chip_date, result.today),
                'is_done': standing.has_minimum_on(chip_date),
            }
            for chip_date in date_range(first_chip_date, result.last_date)
        ],
        'points': points,
        'minimum': minimum,
        'missing': max(minimum - points, 0),
        'surplus': max(points - minimum, 0),
        'progress': min(int(points * 100 / minimum), 100),
    }


@login_required
def day(request, date_text=''):
    challenge = Challenge.current()
    participant = get_paid_participant(challenge, request.user)
    if participant is None:
        return redirect('join')
    today = timezone.localdate()
    if today < challenge.start_date:
        return render(request, 'challenges/not_started.html', {'challenge': challenge})

    result = compute_result(challenge, today)
    date = pick_date(date_text, challenge, result)
    is_editable = result.is_editable(date)
    is_htmx = bool(request.headers.get('HX-Request'))
    form = DayForm(request.POST or None, standing=result.standing_of(participant), date=date, disabled=not is_editable)
    if request.method == 'POST' and is_editable and form.is_valid():
        form.save()
        if not is_htmx:
            return redirect('day', date_text=date.isoformat())
        result = compute_result(challenge, today)
        form = DayForm(standing=result.standing_of(participant), date=date, disabled=False)

    template = 'challenges/_day_panel.html' if is_htmx else 'challenges/day.html'
    return render(request, template, day_context(result, form))


@login_required
def board(request):
    challenge = Challenge.current()
    if challenge is None:
        return redirect('join')
    result = compute_result(challenge, timezone.localdate())
    columns = [
        {
            'date': date,
            'day_number': challenge.day_number(date),
            'minimum': challenge.minimum_points(date),
            'is_locked': challenge.is_locked(date, result.today),
            'last_edit_date': challenge.last_edit_date(date),
        }
        for date in date_range(challenge.start_date, result.last_date)
    ]
    rows = [
        {
            'standing': standing,
            'cells': [
                {
                    'column': column,
                    'state': standing.state_on(column['date']),
                    'points': standing.points_on(column['date']),
                    'entries': standing.date_2_entries.get(column['date'], []),
                }
                for column in columns
            ],
        }
        for standing in result.standings
    ]
    return render(request, 'challenges/board.html', {
        'challenge': challenge,
        'result': result,
        'columns': columns,
        'rows': rows,
    })


@login_required
def join(request):
    challenge = Challenge.current()
    if challenge is None:
        return render(request, 'challenges/join.html', {'challenge': None})
    participant = challenge.participant_for(request.user)
    can_join = participant is None and timezone.localdate() <= challenge.last_join_date
    if request.method == 'POST' and can_join:
        Participant.objects.create(challenge=challenge, user=request.user)
        messages.success(request, _('You signed up. Pay the entry fee; you can log exercise once an admin confirms it.'))
        return redirect('join')
    return render(request, 'challenges/join.html', {
        'challenge': challenge,
        'participant': participant,
        'can_join': can_join,
        'is_closed': participant is None and not can_join,
        'exercises': challenge.exercises.all(),
        'qr_svg': payment_qr_svg(challenge, request.user),
        'payment_message': payment_message(challenge, request.user),
    })


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


@staff_member_required
def manage_participants(request):
    challenge = Challenge.current()
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'approve':
            user = get_object_or_404(get_user_model().objects.waiting_for_approval(), id=request.POST['user'])
            user.is_approved = True
            user.save(update_fields=['is_approved'])
            send_approval_email(request, user)
            messages.success(request, _('%(user)s approved.') % {'user': user})
        elif action == 'reject':
            user = get_object_or_404(get_user_model().objects.waiting_for_approval(), id=request.POST['user'])
            user.delete()
            messages.success(request, _('Registration %(email)s deleted.') % {'email': user.email})
        elif action == 'toggle_paid':
            participant = get_object_or_404(Participant, id=request.POST['participant'], challenge=challenge)
            participant.has_paid = not participant.has_paid
            participant.paid_at = timezone.now() if participant.has_paid else None
            participant.save(update_fields=['has_paid', 'paid_at'])
        return redirect('manage_participants')

    participants = []
    if challenge:
        participants = challenge.participants \
            .select_related('user') \
            .order_by('-has_paid', 'created_at')
    paid_count = sum(participant.has_paid for participant in participants)
    return render(request, 'challenges/manage_participants.html', {
        'challenge': challenge,
        'pending_users': get_user_model().objects.waiting_for_approval(),
        'participants': participants,
        'paid_count': paid_count,
        'collected': paid_count * challenge.entry_fee if challenge else 0,
    })
