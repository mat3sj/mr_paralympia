import datetime
import unicodedata
from decimal import ROUND_DOWN, Decimal, InvalidOperation

import segno
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

from challenges.models import Challenge, Entry, Participant
from challenges.standings import compute_result

MAX_AMOUNT = Decimal('99999')


@login_required
def home(request):
    challenge = Challenge.current()
    if challenge and challenge.participants.filter(user=request.user, has_paid=True).exists():
        return redirect('day')
    return redirect('join')


def parse_amount(exercise, text):
    try:
        amount = Decimal(text.replace(',', '.').strip() or '0')
    except InvalidOperation:
        return None
    if not amount.is_finite():
        return None
    amount = min(max(amount, Decimal(0)), MAX_AMOUNT)
    if exercise.unit == 'reps':
        return amount.to_integral_value(ROUND_DOWN)
    return amount.quantize(Decimal('0.1'), ROUND_DOWN)


def save_day(participant, exercises, date, post_data):
    for exercise in exercises:
        amount = parse_amount(exercise, post_data[f'exercise-{exercise.id}'])
        if amount is None:
            continue
        if amount:
            Entry.objects.update_or_create(
                participant=participant,
                exercise=exercise,
                date=date,
                defaults={'amount': amount},
            )
        else:
            Entry.objects \
                .filter(participant=participant, exercise=exercise, date=date) \
                .delete()


def format_amount(amount):
    return format(amount.normalize(), 'f')


@login_required
def day(request, date_text=''):
    challenge = Challenge.current()
    participant = Participant.objects \
        .filter(challenge=challenge, user=request.user, has_paid=True) \
        .first()
    if participant is None:
        return redirect('join')
    today = timezone.localdate()
    if today < challenge.start_date:
        return render(request, 'challenges/not_started.html', {'challenge': challenge})

    result = compute_result(challenge, today)
    last_date = min(today, result.finished_on or today)
    date = last_date
    if date_text:
        try:
            date = datetime.date.fromisoformat(date_text)
        except ValueError:
            raise Http404
        date = min(max(date, challenge.start_date), last_date)
    is_editable = not challenge.is_locked(date, today) and not (result.finished_on and date > result.finished_on)
    exercises = list(challenge.exercises.all())

    if request.method == 'POST' and is_editable:
        save_day(participant, exercises, date, request.POST)
        if not request.headers.get('HX-Request'):
            return redirect('day', date_text=date.isoformat())
        result = compute_result(challenge, today)

    standing = next(standing for standing in result.standings if standing.participant == participant)
    exercise_id_2_entry = {entry.exercise_id: entry for entry in standing.date_2_entries.get(date, [])}
    rows = []
    for exercise in exercises:
        entry = exercise_id_2_entry.get(exercise.id)
        rows.append({
            'exercise': exercise,
            'amount': format_amount(entry.amount) if entry else '0',
            'points': entry.points if entry else 0,
        })
    points = standing.points_on(date)
    minimum = challenge.minimum_points(date)
    first_chip_date = max(challenge.start_date, today - datetime.timedelta(days=challenge.edit_days + 1))
    chips = []
    chip_date = first_chip_date
    while chip_date <= last_date:
        chips.append({
            'date': chip_date,
            'is_locked': challenge.is_locked(chip_date, today),
            'is_done': standing.points_on(chip_date) >= challenge.minimum_points(chip_date),
        })
        chip_date += datetime.timedelta(days=1)

    context = {
        'challenge': challenge,
        'date': date,
        'today': today,
        'day_number': challenge.day_number(date),
        'is_editable': is_editable,
        'rows': rows,
        'points': points,
        'minimum': minimum,
        'missing': max(minimum - points, 0),
        'surplus': max(points - minimum, 0),
        'strike_dots': [index < standing.strikes for index in range(challenge.max_strikes)],
        'progress': min(int(points * 100 / minimum), 100),
        'is_adaptation': date < challenge.first_strike_date,
        'unlock_until': date + datetime.timedelta(days=challenge.edit_days),
        'chips': chips,
        'standing': standing,
        'result': result,
    }
    template = 'challenges/_day_panel.html' if request.headers.get('HX-Request') else 'challenges/day.html'
    return render(request, template, context)


def cell_state(challenge, standing, date, today):
    if standing.is_out and date > standing.eliminated_on:
        return 'none'
    entries = standing.date_2_entries.get(date)
    if date == today:
        return 'today'
    if standing.points_on(date) >= challenge.minimum_points(date):
        return 'ok'
    if date in standing.strike_dates:
        return 'strike'
    if date < challenge.first_strike_date:
        joined_on = timezone.localdate(standing.participant.created_at)
        return 'adaptation' if entries or date >= joined_on else 'none'
    return 'none'


@login_required
def board(request):
    challenge = Challenge.current()
    if challenge is None:
        return redirect('join')
    today = timezone.localdate()
    result = compute_result(challenge, today)
    last_date = min(today, result.finished_on or today)
    dates = []
    date = challenge.start_date
    while date <= last_date:
        dates.append(date)
        date += datetime.timedelta(days=1)

    rows = []
    for standing in result.standings:
        cells = []
        for date in dates:
            entries = standing.date_2_entries.get(date, [])
            cells.append({
                'date': date,
                'day_number': challenge.day_number(date),
                'minimum': challenge.minimum_points(date),
                'state': cell_state(challenge, standing, date, today),
                'points': standing.points_on(date),
                'entries': entries,
                'is_locked': challenge.is_locked(date, today),
                'unlock_until': date + datetime.timedelta(days=challenge.edit_days),
            })
        rows.append({
            'standing': standing,
            'user': standing.participant.user,
            'cells': cells,
            'strike_dots': [index < standing.strikes for index in range(challenge.max_strikes)],
            'eliminated_day': challenge.day_number(standing.eliminated_on) if standing.eliminated_on else None,
            'is_winner': standing in result.winners,
            'is_at_risk': standing.strikes == challenge.max_strikes - 1,
        })
    columns = [
        {'date': date, 'day_number': challenge.day_number(date), 'minimum': challenge.minimum_points(date)}
        for date in dates
    ]
    return render(request, 'challenges/board.html', {
        'challenge': challenge,
        'columns': columns,
        'rows': rows,
        'result': result,
        'today': today,
    })


def payment_message(challenge, user):
    text = f'{challenge.name} {user}'
    ascii_text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode()
    return ascii_text.replace('*', ' ').upper()[:60]


def payment_qr_svg(challenge, user):
    """QR Platba (SPAYD), the format every Czech banking app reads."""
    spayd = '*'.join([
        'SPD',
        '1.0',
        f'ACC:{challenge.iban}',
        f'AM:{challenge.entry_fee}.00',
        'CC:CZK',
        f'X-VS:{user.id}',
        f'MSG:{payment_message(challenge, user)}',
    ])
    return segno.make(spayd, error='m').svg_inline(scale=5, border=2)


@login_required
def join(request):
    challenge = Challenge.current()
    if challenge is None:
        return render(request, 'challenges/join.html', {'challenge': None})
    participant = Participant.objects \
        .filter(challenge=challenge, user=request.user) \
        .first()
    today = timezone.localdate()
    can_join = participant is None and today <= challenge.last_join_date
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
            user = get_object_or_404(get_user_model(), id=request.POST['user'], is_approved=False)
            user.is_approved = True
            user.save(update_fields=['is_approved'])
            send_approval_email(request, user)
            messages.success(request, _('%(user)s approved.') % {'user': user})
        elif action == 'reject':
            user = get_object_or_404(get_user_model(), id=request.POST['user'], is_approved=False)
            user.delete()
            messages.success(request, _('Registration %(email)s deleted.') % {'email': user.email})
        elif action == 'toggle_paid':
            participant = get_object_or_404(Participant, id=request.POST['participant'], challenge=challenge)
            participant.has_paid = not participant.has_paid
            participant.paid_at = timezone.now() if participant.has_paid else None
            participant.save(update_fields=['has_paid', 'paid_at'])
        return redirect('manage_participants')

    pending_users = get_user_model().objects \
        .filter(is_approved=False, is_staff=False, is_active=True, emailaddress__verified=True) \
        .order_by('date_joined')
    participants = []
    paid_count = 0
    if challenge:
        participants = challenge.participants \
            .select_related('user') \
            .order_by('-has_paid', 'created_at')
        paid_count = sum(participant.has_paid for participant in participants)
    return render(request, 'challenges/manage_participants.html', {
        'challenge': challenge,
        'pending_users': pending_users,
        'participants': participants,
        'paid_count': paid_count,
        'collected': paid_count * challenge.entry_fee if challenge else 0,
    })
