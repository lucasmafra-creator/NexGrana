"""Safe user-facing explanations; never echo a server exception or identifiers."""
def qa_failure(exc):
    text=str(exc).casefold()
    if any(v in text for v in ("pgrst202", "could not find the function", "does not exist")):
        return "O servidor não tem a função de homologação esperada. Peça ao administrador para revisar as migrations 0.24.1 e 0.24.4 em QA e atualizar o cache do schema."
    if any(v in text for v in ("other members", "family has", "only your individual")):
        return "Este espaço não é um ambiente individual descartável só seu. O reset foi bloqueado para proteger os integrantes; use um espaço de QA separado."
    if "not an enrolled sandbox" in text:
        return "Este espaço ainda não foi vinculado como sandbox. Se ele for individual e só seu, use Vincular este espaço como teste antes do reset."
    if any(v in text for v in ("not allowed", "42501", "permission denied")):
        return "Sua conta não está autorizada para esta operação de QA. O administrador precisa conferir seu UID em qa_testers; o endereço de e-mail sozinho não autoriza o reset."
    if any(v in text for v in ("jwt", "expired", "401")):
        return "Sua sessão precisa ser validada novamente. Entre de novo com internet e confira o espaço de teste antes de repetir."
    if any(v in text for v in ("not found", "no longer active")):
        return "O espaço ou sua participação não está mais ativo. Atualize a sessão e selecione o ambiente de QA correto."
    if isinstance(exc,(ConnectionError,TimeoutError)) or any(v in text for v in ("timeout", "connecterror", "network")):
        return "Não consegui confirmar o estado no servidor. Confira a conexão e tente novamente; o reset não será executado apenas no cache local."
    return "O servidor recusou a operação de QA. Preserve os dados e peça ao administrador para revisar autorização, vínculo do sandbox e migrations; nenhum bloqueio será contornado."
