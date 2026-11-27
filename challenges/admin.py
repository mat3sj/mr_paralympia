from django import forms
from django.contrib import admin
from django.utils import timezone

from challenges.models import Challenge, Entry, Exercise, Participant
from challenges.standings import build_scoreboard


class ChallengeForm(forms.ModelForm):
    class Meta:
        model = Challenge
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        current = Challenge.current()
        if self.instance.pk is None and current and not build_scoreboard(current, timezone.localdate()).finished_on:
            raise forms.ValidationError(f'{current} is still running. Only one challenge can run at a time.')
        return cleaned_data


class ExerciseInline(admin.TabularInline):
    model = Exercise
    extra = 0


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    form = ChallengeForm
    list_display = ['name', 'start_date', 'entry_fee']
    inlines = [ExerciseInline]


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ['user', 'challenge', 'has_paid', 'paid_at', 'created_at']
    list_filter = ['challenge', 'has_paid']
    list_select_related = ['user', 'challenge']


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ['date', 'participant', 'exercise', 'amount']
    list_filter = ['participant__challenge', 'exercise']
    list_select_related = ['participant__user', 'exercise']
    date_hierarchy = 'date'
