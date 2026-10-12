"""Configuração da candidata. Trocar para production antes da publicação pública."""
BUILD_CHANNEL = "qa"
QA_ACCOUNT_HINT = "uma conta descartável autorizada por UUID"
# Callback público configurado também no Supabase Auth. Deixe vazio enquanto
# não houver uma página HTTPS real; o cliente nunca deve abrir localhost.
AUTH_REDIRECT_URL = ""
# URL pública do gateway próprio do Nex (ex.: https://nex-api.seudominio.com/v1/chat).
# Pode ser sobrescrita por NEXGRANA_NEX_GATEWAY_URL no Windows/servidor. No
# Android/iOS, preencha antes do build porque variáveis de ambiente móveis não
# são uma forma confiável de configuração em tempo de execução.
NEX_GATEWAY_URL = ""
