"""Strikes, eliminations and the end of a challenge, all derived from entries on every request."""
import collections
import dataclasses
import datetime
from decimal import Decimal

from django.utils import timezone

from challenges.models import Entry

ONE_DAY = datetime.timedelta(days=1)


def date_range(first_date, last_date):
    date = first_date
    while date <= last_date:
        yield date
        date += ONE_DAY


def sum_points(entries):
    return sum((entry.points for entry in entries), Decimal(0))


@dataclasses.dataclass
class Standing:
    """One participant's results; a third strike eliminates only once its day is locked."""

    challenge: object
    participant: object
    today: datetime.date
    date_2_entries: dict
    strike_dates: list
    third_strike_on: datetime.date | None
    is_out: bool
    is_winner: bool = False

    def points_on(self, date):
        return sum_points(self.date_2_entries.get(date, []))

    def has_minimum_on(self, date):
        return self.points_on(date) >= self.challenge.minimum_points(date)

    @property
    def total_points(self):
        return sum_points(entry for entries in self.date_2_entries.values() for entry in entries)

    @property
    def strikes(self):
        return len(self.strike_dates)

    @property
    def strike_dots(self):
        return [index < self.strikes for index in range(self.challenge.strikes_to_eliminate)]

    @property
    def third_strike_day_number(self):
        return self.challenge.day_number(self.third_strike_on)

    @property
    def status(self):
        if self.is_winner:
            return 'winner'
        if self.is_out:
            return 'out'
        if self.third_strike_on:
            return 'being_eliminated'
        if self.strikes == self.challenge.strikes_to_eliminate - 1:
            return 'at_risk'
        return 'playing'

    def day_state(self, date):
        """How a day looks on the board: ok, strike, adaptation, today or none."""
        if self.is_out and date > self.third_strike_on:
            return 'none'
        if date == self.today:
            return 'today'
        if self.has_minimum_on(date):
            return 'ok'
        if date in self.strike_dates:
            return 'strike'
        joined_on = timezone.localdate(self.participant.created_at)
        if date < self.challenge.first_strike_date and (date in self.date_2_entries or date >= joined_on):
            return 'adaptation'
        return 'none'


def build_standing(challenge, participant, date_2_entries, last_date, today):
    strike_dates = [
        date
        for date in date_range(challenge.first_strike_date, last_date)
        if sum_points(date_2_entries.get(date, [])) < challenge.minimum_points(date)
    ]
    third_strike_on = None
    if len(strike_dates) >= challenge.strikes_to_eliminate:
        third_strike_on = strike_dates[challenge.strikes_to_eliminate - 1]
    is_out = third_strike_on is not None and challenge.is_locked(third_strike_on, today)
    if is_out:
        strike_dates = strike_dates[:challenge.strikes_to_eliminate]
    return Standing(
        challenge=challenge,
        participant=participant,
        today=today,
        date_2_entries=date_2_entries,
        strike_dates=strike_dates,
        third_strike_on=third_strike_on,
        is_out=is_out,
    )


def find_end(standings):
    """The locked day that leaves one participant, or none (they share the win), and the winning participants."""
    alive = len(standings)
    if alive < 2:
        return None, []
    elimination_dates = sorted({standing.third_strike_on for standing in standings if standing.is_out})
    for date in elimination_dates:
        eliminated = [standing for standing in standings if standing.is_out and standing.third_strike_on == date]
        alive -= len(eliminated)
        if alive == 1:
            return date, [standing.participant for standing in standings if not standing.is_out]
        if alive == 0:
            return date, [standing.participant for standing in eliminated]
    return None, []


@dataclasses.dataclass
class Scoreboard:
    challenge: object
    today: datetime.date
    standings: list
    finished_on: datetime.date | None

    @property
    def winners(self):
        return [standing for standing in self.standings if standing.is_winner]

    @property
    def last_date(self):
        """The last day that is played: today, or the day the challenge ended."""
        return min(self.today, self.finished_on or self.today)

    def is_editable(self, date):
        return date <= self.last_date and not self.challenge.is_locked(date, self.today)

    def standing_of(self, participant):
        return next(standing for standing in self.standings if standing.participant == participant)


def build_scoreboard(challenge, today):
    participants = challenge.participants \
        .filter(has_paid=True) \
        .select_related('user')
    entries = Entry.objects \
        .filter(participant__in=participants) \
        .select_related('exercise')
    participant_id_2_date_2_entries = collections.defaultdict(lambda: collections.defaultdict(list))
    for entry in entries:
        participant_id_2_date_2_entries[entry.participant_id][entry.date].append(entry)

    def build_standings(last_date):
        return [
            build_standing(challenge, participant, participant_id_2_date_2_entries[participant.id], last_date, today)
            for participant in participants
        ]

    standings = build_standings(today - ONE_DAY)
    finished_on, winners = find_end(standings)
    if finished_on:
        # Days after the end don't count, so the winners can't be eliminated afterwards.
        standings = build_standings(finished_on)
        for standing in standings:
            standing.is_winner = standing.participant in winners
    standings.sort(key=lambda standing: (standing.status == 'out', standing.strikes, -standing.total_points))
    return Scoreboard(challenge=challenge, today=today, standings=standings, finished_on=finished_on)
