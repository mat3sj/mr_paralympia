from django import forms

from challenges.models import Entry


def field_name(exercise):
    return f'exercise-{exercise.id}'


class DayForm(forms.Form):
    """One amount per exercise for one day of one player; an empty or zero amount deletes the entry."""

    def __init__(self, *args, standing, date, disabled, **kwargs):
        super().__init__(*args, **kwargs)
        self.standing = standing
        self.date = date
        self.exercises = list(standing.challenge.exercises.all())
        exercise_id_2_amount = {entry.exercise_id: entry.amount for entry in standing.date_2_entries.get(date, [])}
        for exercise in self.exercises:
            amount = exercise_id_2_amount.get(exercise.id, 0)
            self.fields[field_name(exercise)] = forms.DecimalField(
                min_value=0,
                max_value=99999,
                decimal_places=1 if exercise.unit == 'km' else 0,
                required=False,
                localize=True,
                disabled=disabled,
                initial=amount if exercise.unit == 'km' else int(amount),
                widget=forms.TextInput(attrs={'inputmode': 'decimal', 'autocomplete': 'off'}),
            )

    def field_for(self, exercise):
        return self[field_name(exercise)]

    def save(self):
        for exercise in self.exercises:
            amount = self.cleaned_data[field_name(exercise)]
            if amount:
                Entry.objects.update_or_create(
                    participant=self.standing.participant,
                    exercise=exercise,
                    date=self.date,
                    defaults={'amount': amount},
                )
            else:
                Entry.objects \
                    .filter(participant=self.standing.participant, exercise=exercise, date=self.date) \
                    .delete()
