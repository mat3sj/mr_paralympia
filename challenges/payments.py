"""QR Platba (SPAYD), the payment QR format every Czech banking app reads."""
import unicodedata

import segno


def payment_message(challenge, user):
    text = f'{challenge.name} {user}'
    ascii_text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode()
    return ascii_text.replace('*', ' ').upper()[:60]


def payment_qr_svg(challenge, user):
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
