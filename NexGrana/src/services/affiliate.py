"""Validação local da camada de afiliados.

Ofertas comerciais são secundárias: não entram no motor financeiro nem no
ranking de compra. Nenhum clique é enviado remotamente nesta versão.
"""
from datetime import datetime, timezone
from urllib.parse import urlsplit, parse_qs
import unicodedata

from .offers import validate_offer_url, validate_partner_url

DISCLOSURE = 'Link afiliado: o NexGrana pode receber uma comissão. Consulte preço e condições no parceiro. Isso não altera a análise financeira nem torna a compra recomendada.'
HOSTS = {'meli.la', 'mercadolivre.com.br', 'www.mercadolivre.com.br'}
ALLOWED_QUERY = {'matt_tool','matt_word','matt_source','utm_source','utm_medium','utm_campaign'}


def _search_text(value):
    return unicodedata.normalize('NFKD', str(value or '')).encode('ascii','ignore').decode().casefold()


def filter_offers(rows, query='', category='Todos'):
    """Filtra o catálogo sem usar saldo, despesas ou valor de comissão."""
    needle=_search_text(query).strip()
    selected=_search_text(category).strip()
    result=[]
    for row in rows or []:
        row_category=_search_text(row.get('category'))
        if selected and selected != 'todos' and row_category != selected:
            continue
        haystack=' '.join(_search_text(row.get(key)) for key in (
            'title','subtitle','category','provider','compatibility','search_tags'
        ))
        if needle and needle not in haystack:
            continue
        result.append(row)
    return result


def active_offers(rows, now=None, platform=None, allowed_hosts=None):
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
            if not validate_partner_url(url, set(allowed_hosts) if allowed_hosts is not None else HOSTS):
                continue
            if parsed.port not in (None,443) or parsed.fragment:
                continue
            if row.get('availability')=='out_of_stock':
                continue
            if row.get('source')=='sim_labs' and row.get('price') is not None:
                verified=datetime.fromisoformat(str(row.get('verified_at') or '').replace('Z','+00:00'))
                age=(now-verified).total_seconds()
                if age>86400 or age < -300:continue
            if row.get('source')!='sim_labs' and not set(parse_qs(parsed.query)).issubset(ALLOWED_QUERY):
                continue
            clean={**row,'badge':'Link de parceiro','commercial':True}
            result.append(clean)
        except (KeyError, ValueError, TypeError):
            continue
    # A ordem do backend é preservada. Não reordenamos por comissão nem por
    # qualquer campo comercial dentro do cliente.
    return result
