import datetime

from django.conf import settings
from django.db import models
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _


class Challenge(models.Model):
    name = models.CharField(_('name'), max_length=100)
    start_date = models.DateField(_('start date'))
    base_points = models.PositiveIntegerField(_('minimum on the first day'), default=10)
    daily_increment = models.PositiveIntegerField(_('daily increase of the minimum'), default=5)
    adaptation_days = models.PositiveIntegerField(_('adaptation days without strikes'), default=10)
    edit_days = models.PositiveIntegerField(_('days a record stays editable'), default=5)
    max_strikes = models.PositiveIntegerField(_('strikes that eliminate a player'), default=3)
    entry_fee = models.PositiveIntegerField(_('entry fee (CZK)'))
    bank_account = models.CharField(_('bank account'), max_length=30, help_text='Czech format, e.g. 670100-2210457032/6210')
    rules_cs = models.TextField(_('rules in Czech'))
    rules_en = models.TextField(_('rules in English'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return self.name

    @classmethod
    def current(cls):
        return cls.objects.first()

    def day_number(self, date):
        return (date - self.start_date).days + 1

    def date_of_day(self, day_number):
        return self.start_date + datetime.timedelta(days=day_number - 1)

    def minimum_points(self, date):
        return self.base_points + self.daily_increment * (self.day_number(date) - 1)

    @property
    def first_strike_date(self):
        return self.date_of_day(self.adaptation_days + 1)

    @property
    def last_join_date(self):
        """Late players can still back-fill the first day that counts for strikes."""
        return self.date_of_day(self.adaptation_days + self.edit_days)

    def last_edit_date(self, date):
        return date + datetime.timedelta(days=self.edit_days)

    def is_locked(self, date, today):
        return today > self.last_edit_date(date)

    def participant_for(self, user):
        return self.participants \
            .filter(user=user) \
            .first()

    @property
    def iban(self):
        account, bank_code = self.bank_account.split('/')
        prefix, _separator, number = account.rpartition('-')
        bban = bank_code + prefix.zfill(6) + number.zfill(10)
        check_digits = 98 - int(bban + '123500') % 97  # 'CZ00' moved to the end, letters as numbers
        return f'CZ{check_digits:02d}{bban}'

    @property
    def rules(self):
        return self.rules_en if get_language() == 'en' else self.rules_cs


class Exercise(models.Model):
    UNIT_CHOICES = [
        ('reps', _('repetitions')),
        ('km', _('kilometres')),
    ]

    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='exercises')
    name_cs = models.CharField(_('name in Czech'), max_length=50)
    name_en = models.CharField(_('name in English'), max_length=50)
    points_per_unit = models.DecimalField(_('points per unit'), max_digits=6, decimal_places=2)
    unit = models.CharField(_('unit'), max_length=4, choices=UNIT_CHOICES, default='reps')
    order = models.PositiveSmallIntegerField(_('order'), default=0)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return self.name

    @property
    def name(self):
        return self.name_en if get_language() == 'en' else self.name_cs

    @property
    def step(self):
        return '0.1' if self.unit == 'km' else '1'


class Participant(models.Model):
    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='participants')
    has_paid = models.BooleanField(_('paid'), default=False)
    paid_at = models.DateTimeField(_('paid at'), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['user__first_name', 'user__last_name']
        constraints = [
            models.UniqueConstraint(fields=['challenge', 'user'], name='unique_participant'),
        ]

    def __str__(self):
        return f'{self.user} – {self.challenge}'


class Entry(models.Model):
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='entries')
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name='entries')
    date = models.DateField(_('date'))
    amount = models.DecimalField(_('amount'), max_digits=7, decimal_places=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'entries'
        ordering = ['date', 'exercise__order']
        constraints = [
            models.UniqueConstraint(fields=['participant', 'exercise', 'date'], name='unique_entry'),
        ]

    def __str__(self):
        return f'{self.participant.user} {self.date} {self.exercise}: {self.amount}'

    @property
    def points(self):
        return self.amount * self.exercise.points_per_unit
