"""Validação local da camada de afiliados.

Ofertas comerciais são secundárias: não entram no motor financeiro nem no
ranking de compra. Nenhum clique é enviado remotamente nesta versão.
"""
from datetime import datetime, timezone
from urllib.parse import urlsplit, parse_qs

from .offers import validate_offer_url

DISCLOSURE = 'Link de parceiro. O NexGrana pode receber comissão por este link. Isso não altera a análise financeira nem torna a compra recomendada.'
HOSTS = {'meli.la', 'mercadolivre.com.br', 'www.mercadolivre.com.br'}
ALLOWED_QUERY = {'matt_tool','matt_word','matt_source','utm_source','utm_medium','utm_campaign'}


def active_offers(rows, now=None, platform=None):
    now = now or datetime.now(timezone.utc)
    result = []
    for row in rows or []:
        try:
            url = str(row['url'])
            parsed = urlsplit(url)
            expires = datetime.fromisoformat(str(row['expires_at']).replace('Z','+00:00'))
            row_platform=(row.get('platform') or '').strip().lower()
            if platform and row_platform and row_platform not in {'all',str(platform).lower()}:
                continue
            if not row.get('enabled') or expires <= now:
                continue
            if not validate_offer_url(url, HOSTS):
                continue
            if parsed.port not in (None,443) or parsed.fragment:
                continue
            if not set(parse_qs(parsed.query)).issubset(ALLOWED_QUERY):
                continue
            clean={**row,'badge':'Link de parceiro','commercial':True}
            result.append(clean)
        except (KeyError, ValueError, TypeError):
            continue
    # A ordem do backend é preservada. Não reordenamos por comissão nem por
    # qualquer campo comercial dentro do cliente.
    return result
