"""Check Nex gateway wiring without printing or requesting any credentials."""
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import urlopen

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from services.nex_gateway import GATEWAY_ENV, validate_gateway_url


def main():
    from build_config import NEX_GATEWAY_URL

    configured = os.getenv(GATEWAY_ENV, "").strip() or NEX_GATEWAY_URL.strip()
    if not configured:
        print("NEX LOCAL: gateway HTTPS não configurado neste projeto.")
        print("Publique gateway/app.py com Supabase e provedor configurados no servidor.")
        print("Depois preencha NEX_GATEWAY_URL em src/build_config.py e gere novamente o APK.")
        print("No Windows, também pode definir NEXGRANA_NEX_GATEWAY_URL no ambiente antes de executar.")
        return 2
    try:
        chat_url = validate_gateway_url(configured)
    except ValueError as exc:
        print(f"NEX CONFIGURAÇÃO INVÁLIDA: {exc}")
        return 2
    parsed = urlparse(chat_url)
    health = f"https://{parsed.netloc}/health"
    print(f"Gateway configurado: {parsed.netloc} (HTTPS). Checando /health sem token...")
    try:
        with urlopen(health, timeout=8) as response:
            status = response.status
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        print(f"Gateway inacessível: {type(exc).__name__}. Verifique deploy, DNS e TLS.")
        return 1
    if status != 200:
        print(f"Gateway respondeu HTTP {status}; esperado 200.")
        return 1
    print("/health: HTTP 200. Ainda é preciso testar login, consentimento e uma resposta real no app.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
