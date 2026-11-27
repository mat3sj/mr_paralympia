"""Strikes, eliminations and the end of a challenge, all derived from entries on every request."""
import collections
import dataclasses
import datetime
from decimal import Decimal

from challenges.models import Entry

ONE_DAY = datetime.timedelta(days=1)


def sum_points(entries):
    return sum((entry.points for entry in entries), Decimal(0))


@dataclasses.dataclass
class Standing:
    participant: object
    date_2_entries: dict
    strike_dates: list
    eliminated_on: datetime.date | None
    is_out: bool

    def points_on(self, date):
        return sum_points(self.date_2_entries.get(date, []))

    @property
    def total_points(self):
        return sum_points(entry for entries in self.date_2_entries.values() for entry in entries)

    @property
    def strikes(self):
        return len(self.strike_dates)


@dataclasses.dataclass
class Result:
    standings: list
    finished_on: datetime.date | None
    winners: list


def find_strikes(challenge, date_2_entries, last_date):
    strike_dates = []
    date = challenge.first_strike_date
    while date <= last_date:
        if sum_points(date_2_entries.get(date, [])) < challenge.minimum_points(date):
            strike_dates.append(date)
        date += ONE_DAY
    return strike_dates


def build_standing(challenge, participant, date_2_entries, last_date, today):
    """A third strike on a day that can still be edited only threatens; it eliminates once the day locks."""
    strike_dates = find_strikes(challenge, date_2_entries, last_date)
    eliminated_on = None
    if len(strike_dates) >= challenge.max_strikes:
        eliminated_on = strike_dates[challenge.max_strikes - 1]
    is_out = eliminated_on is not None and challenge.is_locked(eliminated_on, today)
    if is_out:
        strike_dates = strike_dates[:challenge.max_strikes]
    return Standing(
        participant=participant,
        date_2_entries=date_2_entries,
        strike_dates=strike_dates,
        eliminated_on=eliminated_on,
        is_out=is_out,
    )


def find_end(standings):
    """The challenge ends on the locked day that leaves one player, or none (they share the win)."""
    alive = len(standings)
    if alive < 2:
        return None, []
    elimination_dates = sorted({standing.eliminated_on for standing in standings if standing.is_out})
    for date in elimination_dates:
        eliminated = [standing for standing in standings if standing.is_out and standing.eliminated_on == date]
        alive -= len(eliminated)
        if alive == 1:
            return date, [standing for standing in standings if not standing.is_out]
        if alive == 0:
            return date, eliminated
    return None, []


def compute_result(challenge, today):
    participants = challenge.participants \
        .filter(has_paid=True) \
        .select_related('user')
    entries = Entry.objects \
        .filter(participant__in=participants) \
        .select_related('exercise')
    participant_id_2_date_2_entries = collections.defaultdict(lambda: collections.defaultdict(list))
    for entry in entries:
        participant_id_2_date_2_entries[entry.participant_id][entry.date].append(entry)

    yesterday = today - ONE_DAY
    standings = [
        build_standing(challenge, participant, participant_id_2_date_2_entries[participant.id], yesterday, today)
        for participant in participants
    ]
    finished_on, winners = find_end(standings)
    if finished_on:
        # Days after the end don't count, so the winners can't be eliminated afterwards.
        standings = [
            build_standing(challenge, standing.participant, standing.date_2_entries, finished_on, today)
            for standing in standings
        ]
        winner_ids = {winner.participant.id for winner in winners}
        winners = [standing for standing in standings if standing.participant.id in winner_ids]
    standings.sort(key=lambda standing: (standing.is_out, standing.strikes, -standing.total_points))
    return Result(standings=standings, finished_on=finished_on, winners=winners)
