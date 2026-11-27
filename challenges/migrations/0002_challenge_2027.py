import datetime
from decimal import Decimal

from django.db import migrations

RULES_CS = """\
Každý den nasbírej aspoň denní minimum bodů. První den je to 10 bodů, každý další den o 5 víc (10. den 55, 30. den 155).
Prvních 10 dní je adaptační období: když minimum nesplníš, nic se neděje.
Od 11. dne je každý den pod minimem strike. Prázdný den je taky strike. Třetí strike znamená konec.
Záznam můžeš doplnit nebo opravit ještě 5 dní po daném dni, pak se zamkne. Do té doby jde strike opravit.
Přidat se můžeš nejpozději v pátek 15. 1. 2027. Zmeškané dny si doplň, dokud nejsou zamčené.
Zapisovat můžeš, až admin potvrdí startovné 50 Kč.
Výzva končí, když zůstane poslední hráč. Když všichni zbývající dostanou třetí strike ve stejný den, výhru si rozdělí.
Body zapisuj poctivě. Paralympionici taky nepodvádějí."""

RULES_EN = """\
Collect at least the daily minimum every day. The first day it is 10 points, then 5 more every day (day 10: 55, day 30: 155).
The first 10 days are an adaptation period: missing the minimum costs nothing.
From day 11 every day below the minimum is a strike. An empty day is a strike too. The third strike ends your challenge.
You can add or fix a record for 5 more days, then it locks. Until then a strike can still be fixed.
You can join until Friday 15 January 2027. Fill in the days you missed before they lock.
You can log exercise once an admin confirms the 50 CZK entry fee.
The challenge ends when one player is left. If all remaining players get their third strike on the same day, they share the win.
Log honestly. Paralympians don't cheat either."""

EXERCISES = [
    ('Kliky', 'Push-ups', Decimal('1'), 'reps'),
    ('Dřepy', 'Squats', Decimal('1'), 'reps'),
    ('Sedy-lehy', 'Sit-ups', Decimal('2'), 'reps'),
    ('Shyby', 'Pull-ups', Decimal('4'), 'reps'),
    ('Běh', 'Running', Decimal('20'), 'km'),
]


def create_challenge(apps, schema_editor):
    Challenge = apps.get_model('challenges', 'Challenge')
    Exercise = apps.get_model('challenges', 'Exercise')
    challenge = Challenge.objects.create(
        name='Výzva 2027',
        start_date=datetime.date(2027, 1, 1),
        base_points=10,
        daily_increment=5,
        adaptation_days=10,
        edit_days=5,
        max_strikes=3,
        entry_fee=50,
        bank_account='670100-2210457032/6210',
        rules_cs=RULES_CS,
        rules_en=RULES_EN,
    )
    for order, (name_cs, name_en, points_per_unit, unit) in enumerate(EXERCISES):
        Exercise.objects.create(
            challenge=challenge,
            name_cs=name_cs,
            name_en=name_en,
            points_per_unit=points_per_unit,
            unit=unit,
            order=order,
        )


def delete_challenge(apps, schema_editor):
    apps.get_model('challenges', 'Challenge').objects \
        .filter(name='Výzva 2027', start_date=datetime.date(2027, 1, 1)) \
        .delete()


class Migration(migrations.Migration):
    dependencies = [
        ('challenges', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_challenge, delete_challenge),
    ]
