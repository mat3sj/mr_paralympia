# Mr. Paralympia

Paralympionici trénují roky, padají a znovu vstávají, a stejně nastoupí. My máme problém s deseti kliky.
Tahle aplikace hlídá, jestli to vydržíme aspoň do jara: každý den o pět bodů víc, tři zaváhání a končíš.
Kdo zůstane poslední, je Mr. Paralympia.

## Jak to funguje

- Registrace e-mailem a heslem (s ověřením e-mailu a Cloudflare Turnstile proti botům) nebo přes Google.
  Každý nový účet musí schválit admin.
- Hráč se přihlásí do výzvy, zaplatí startovné přes QR Platbu a zapisovat může, až admin platbu potvrdí.
- Denní minimum = `base_points + daily_increment × (den − 1)`. Během adaptace se nesplnění netrestá,
  potom je každý den pod minimem (i prázdný) strike. Den jde upravovat ještě `edit_days` dní,
  třetí strike vyřadí hráče, až se jeho den zamkne.
- Výzva končí, když zůstane jediný hráč. Když všichni zbývající vypadnou ve stejný den, dělí se o výhru.
- Striky, vyřazení ani konec se neukládají, počítají se ze záznamů při každém zobrazení
  (`challenges/standings.py`).
- Aktuální výzva je ta s nejpozdějším startem. Novou jde založit v Django adminu, až ta předchozí skončí.
- První výzvu (start 1. 1. 2027) zakládá datová migrace `challenges/migrations/0002_challenge_2027.py`.
- Čeština je výchozí, angličtinu si uživatel přepne ručně. Jazyk prohlížeče se ignoruje.

## Lokální vývoj

Potřebuješ Python 3.13 a `gettext` (kvůli překladům).

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export DJANGO_DEBUG=1
python manage.py compilemessages
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Bez `POSTGRES_DB` běží na SQLite, bez `EMAIL_HOST_USER` se e-maily vypisují do konzole
a bez `TURNSTILE_SECRET_KEY` se ochrana proti botům přeskočí.

Po změně textů:

```bash
python manage.py makemessages -l cs -l en --ignore='*/migrations/*'
python manage.py compilemessages
```

## Nasazení na DigitalOcean

1. Založ Droplet s Ubuntu (nejmenší stačí) a nainstaluj Docker podle
   [návodu](https://docs.docker.com/engine/install/ubuntu/).
2. U domény nastav A záznam na IP dropletu.
3. Na dropletu:

   ```bash
   git clone https://github.com/mat3sj/mr_paralympia.git /srv/mr_paralympia
   cd /srv/mr_paralympia
   cp .env.example .env   # a vyplň
   docker compose up -d --build
   docker compose exec web python manage.py createsuperuser
   ```

   Caddy si sám vyřídí HTTPS certifikát pro `DOMAIN`.
4. Aktualizace: `git pull && docker compose up -d --build`.
5. Záloha databáze každou noc (`crontab -e`):

   ```
   0 3 * * * cd /srv/mr_paralympia && docker compose exec -T db pg_dump -U paralympia paralympia | gzip > /srv/backups/paralympia-$(date +\%F).sql.gz
   ```
