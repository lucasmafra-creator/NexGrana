"""Fronteira única da conversa do Nex.

A camada conversacional interpreta a intenção, mas números financeiros críticos
vêm dos serviços determinísticos.  O cliente não contém chave de LLM e não
finge que há IA externa conectada quando não há backend configurado.
"""
from dataclasses import dataclass
from collections import deque
import logging
import re
import unicodedata
from .finance_engine import affordable_acquisitions, goal_scenarios
from .journeys import journey_steps
from .nex_gateway import GatewayUnavailable, NexGatewayClient, prepare_gateway_payload
from .nex_conversation import ChatIntent, classify_intent_with_history, preferred_name_command
from .nex_local_knowledge import local_answer

logger = logging.getLogger(__name__)


def safety_response(text):
    """Recusa pedidos operacionais nocivos sem bloquear dúvidas defensivas."""
    q = re.sub(r"\s+", " ", str(text or "").casefold()).strip()
    defensive = any(term in q for term in (
        "como me proteger", "como evitar", "segurança defensiva", "denunciar",
        "recuperar minha conta", "minha conta foi", "prevenir", "proteção",
    ))
    extraction = any(term in q for term in (
        "ignore as instruções", "ignore suas instruções", "prompt interno",
        "revele o segredo", "mostre a chave", "service_role", "outra família",
        "dados de outro usuário", "dados de outro usuario",
    ))
    cyber = any(term in q for term in (
        "roubar senha", "clonar cartão", "clonar cartao", "invadir conta",
        "criar malware", "ransomware", "phishing para", "burlar autenticação",
        "burlar autenticacao", "fraudar pagamento",
    ))
    violence = any(term in q for term in (
        "como matar", "como sequestrar", "fabricar bomba", "ocultar cadáver",
        "ocultar cadaver",
    ))
    if extraction:
        return ("Não posso revelar instruções internas, segredos ou dados de outra conta/família. "
                "Posso explicar como o NexGrana protege o acesso ou ajudar você a revisar seus próprios dados.")
    if violence or (cyber and not defensive):
        return ("Não posso ajudar a executar fraude, invasão, roubo de credenciais ou violência. "
                "Se a intenção é proteção, denúncia ou recuperação da sua própria conta, descreva esse objetivo e eu ajudo por um caminho seguro.")
    return None


@dataclass(frozen=True)
class Context:
    source: str
    household_id: str
    member_id: str
    month: str
    entity_id: str | None = None
    action: str | None = None
    payload: dict | None = None
    request_id: str | None = None
    conversation_id: str | None = None
    snapshot_reference: str | None = None
    history: tuple | None = None


def brl(value):
    return f'R$ {value:,.2f}'.replace(',','X').replace('.',',').replace('X','.')


class NexEngine:
    def __init__(self, app, gateway=None):
        self.app = app
        self.last_mode = "local"
        self.connection_state = "ready" if gateway is not None else "local"
        self.last_gateway_error = ""
        self._outage_announced = False
        self._recent_fallbacks = deque(maxlen=3)
        if gateway is not None:
            self.gateway = gateway
        else:
            try:
                supplier = getattr(app.cloud, "gateway_access_token", lambda: None)
                self.gateway = NexGatewayClient.from_environment(supplier)
            except ValueError as exc:
                logger.warning("nex_gateway_config_invalid kind=%s", type(exc).__name__)
                self.gateway = None
        if self.gateway is not None:
            self.connection_state = "ready"

    @staticmethod
    def _generic_local_response(text):
        normalized = str(text or "").casefold()
        return normalized.startswith((
            "tô acompanhando", "to acompanhando", "entendi a pergunta",
            "boa pergunta",
        ))

    def _honest_general_fallback(self):
        if self.gateway is None:
            prefix="O modo online ainda não foi configurado nesta versão; "
        elif self.connection_state == "offline":
            prefix="O modo online falhou nesta tentativa; "
        else:
            prefix="O modo online não foi ativado para esta conversa; "
        if self._outage_announced:
            prefix=""
        self._outage_announced=True
        variants=(
            prefix+"não quero inventar uma resposta. Posso ajudar com funções do app; respostas gerais precisam do serviço online autorizado.",
            "Ainda estou com você, mas essa pergunta precisa do modo online para uma resposta boa. As consultas aos seus registros continuam funcionando localmente.",
            "Não consegui alcançar a conversa online neste momento. Reformule quando a conexão voltar ou me peça algo sobre seu mês, metas, contas ou uso do app.",
        )
        chosen=next((item for item in variants if item not in self._recent_fallbacks),variants[0])
        self._recent_fallbacks.append(chosen)
        return chosen

    def _external_ai_allowed(self):
        try:
            return bool((self.app.cloud.get_privacy_consents() or {}).get("external_ai"))
        except Exception as exc:
            logger.info("nex_consent_read_failed kind=%s", type(exc).__name__)
            return False

    def _online_reply(self, text, context):
        if not self.gateway or not self._external_ai_allowed():
            return None
        self.connection_state="connecting"
        history = context.history if context.history is not None else getattr(self.app,"chat_messages",[])
        intent = classify_intent_with_history(text,history,context.action)
        data = self.app.dashboard_data() if intent == ChatIntent.FINANCIAL else None
        payload = prepare_gateway_payload(
            text,
            request_id=context.request_id or "local",
            locale="pt-BR",
            consent=True,
            financial_context=data,
            history=history,
            intent=intent.value,
            preferences=getattr(self.app, "nex_preferences", lambda: {})(),
        )
        payload["household_id"] = context.household_id  # consent is checked server-side in this scope
        reply=self.gateway.reply(payload)
        self.connection_state="online"
        self.last_gateway_error=""
        self._outage_announced=False
        return reply

    def _local_small_talk(self,text):
        q=re.sub(r"[^a-zà-ÿ0-9 ]+"," ",str(text or "").casefold())
        tokens=[token for token in re.sub(r"\s+"," ",q).strip().split() if token not in {"nex","bro","mano","amigo"}]
        base=" ".join(tokens)
        name=(getattr(self.app,"nex_preferences",lambda:{})() or {}).get("preferred_name") or ""
        called=f", {name}" if name else ""
        if base in {"oi","olá","ola","opa","eae","e ai","e aí","fala","salve","bom dia","boa tarde","boa noite"}:
            return f"Opa{called}! Tô por aqui. Quer conversar, entender seu mês ou planejar alguma coisa?"
        if base in {"suave","de boa","tranquilo","tudo bem","blz","beleza"}:
            return f"Tudo certo por aqui{called} 😄 E com você? Pode falar normal — eu acompanho o assunto."
        if base in {"valeu","obrigado","obrigada","tmj","tamo junto"}:
            return f"Tamo junto{called}! Quando quiser, continuamos daqui."
        return None

    def _nex_connection_help(self, text):
        """Answer operational questions locally using actual runtime state."""
        normalized=unicodedata.normalize("NFKD",str(text or "").casefold())
        normalized="".join(char for char in normalized if not unicodedata.combining(char))
        phrases=("modo online", "nex online", "ia externa", "ativar ia", "ativar o nex", "conectado", "conexao do nex", "nex completo")
        if not any(phrase in normalized for phrase in phrases):
            return None
        if self.gateway is None:
            return ("O Nex está no modo local porque o serviço de conversa online ainda não foi configurado "
                    "nesta versão do aplicativo. Você pode continuar usando suas consultas financeiras locais. "
                    "Quando o serviço estiver disponível, a opção de autorização aparecerá aqui no Nex.")
        if not self._external_ai_allowed():
            return ("O serviço de conversa foi configurado, mas você ainda não autorizou a IA externa. "
                    "Abra Configurações → Privacidade e exportação → IA externa para escolher se quer ativar. "
                    "Se preferir, continuo no modo local.")
        if self.connection_state == "online":
            return ("A última resposta desta conversa veio do serviço online. "
                    "Se a conexão mudar, aviso e volto ao modo local sem inventar dados.")
        if self.connection_state == "offline":
            return ("A conversa online falhou na última tentativa. Seus dados e consultas locais continuam acessíveis; "
                    "pode tentar novamente quando a conexão voltar.")
        return ("O serviço online está configurado e autorizado, mas ainda não confirmei uma resposta dele "
                "nesta conversa. Envie uma pergunta para testar a conexão.")

    def respond(self, text, context):
        try:
            self.last_mode = "local"
            if context.household_id != str(self.app.cloud._hid()):
                raise ValueError('Contexto alterado')
            if context.member_id and context.member_id not in {str(m.get('id')) for m in self.app.members()}:
                raise ValueError('Perfil fora da família')
            guarded = safety_response(text)
            if guarded:
                return guarded
            q = self.app._norm(text)
            preference_command = preferred_name_command(text)
            if preference_command:
                action, name = preference_command
                if action == "clear":
                    getattr(self.app, "forget_nex_preferred_name", lambda: None)()
                    return "Combinado. Não vou usar apelido para falar com você. Você pode mudar isso depois nas configurações do Nex."
                remember = any(term in q for term in ("sempre", "lembre", "proximas conversas", "próximas conversas"))
                getattr(self.app, "set_nex_preferred_name", lambda *_args, **_kwargs: None)(name, remember=remember)
                suffix = " Vou lembrar nas próximas conversas." if remember else " Vou usar nesta conversa; se quiser que eu lembre nas próximas, é só pedir."
                return f"Fechado, {name}.{suffix}"

            connection_help=self._nex_connection_help(text)
            if connection_help:
                return connection_help

            small_talk=self._local_small_talk(text)
            if small_talk:
                return small_talk
            if context.action in {None, "message"}:
                knowledge = local_answer(text)
                if knowledge:
                    return knowledge
            history = context.history if context.history is not None else getattr(self.app,"chat_messages",[])
            intent = classify_intent_with_history(text,history,context.action)
            online_attempted = False
            if intent == ChatIntent.GENERAL:
                online_attempted = True
                try:
                    online_response = self._online_reply(text, context)
                    if online_response:
                        self.last_mode = "online"
                        return online_response
                except GatewayUnavailable as exc:
                    self.last_mode = "fallback"
                    self.connection_state="offline"
                    self.last_gateway_error=str(exc)
                    logger.info('nex_gateway_unavailable kind=%s', type(exc).__name__)
            # Casual chat must not wait for unrelated Supabase goal queries.
            def scoped_goals():
                return [goal for goal in (self.app.cloud.list_goals() or [])
                        if not goal.get('member_id') or str(goal.get('member_id')) == str(context.member_id)]

            if context.action == 'continue_journey':
                payload=context.payload or {}
                title=payload.get('title') or context.entity_id or 'sua trilha'
                steps=journey_steps(title)
                progress=max(0,min(int(payload.get('progress') or 0),len(steps)))
                if progress >= len(steps):
                    return (f'Sua Trilha Nex de {title} está concluída. Agora compare receita, custos, horas e recorrência antes de ampliar. '
                            'Se quiser, me diga o resultado registrado e eu ajudo a interpretar sem prometer ganho.')
                name,mission=steps[progress]
                return (f'Trilha Nex — {title}. Etapa {progress+1}/{len(steps)}: {name}.\n'
                        f'Próxima missão: {mission.rstrip(".")}.\n'
                        'Vamos fazer uma coisa por vez. Me diga o que já está pronto nessa etapa e eu continuo dali.')

            if context.action == 'simulate_goal' or ('simul' in q and 'meta' in q):
                goals=scoped_goals()
                goal = next((g for g in goals if (context.entity_id and str(g['id']) == context.entity_id)
                             or (not context.entity_id and self.app._norm(g['name']) in q)), None)
                if not goal:
                    return 'Não identifiquei a meta. Abra Planejamento e toque em Simular na meta desejada.'
                d = self.app.dashboard_data()
                s = goal_scenarios(
                    goal,
                    d['projected_monthly_result'],
                    d['projected_balance'],
                    goals,
                    reserve=self.app.preferences.get('minimum_reserve',0),
                )
                rec=('O cenário cabe na margem conservadora dos dados registrados.' if s['fits']
                     else 'Eu ajustaria o prazo ou a entrada antes de assumir esse ritmo.')
                return (f"Simulação de {goal['name']} — fonte: meta e caixa em {d['as_of']}.\n"
                        f"• Falta {brl(s['remaining'])}. Para manter o prazo: {brl(s['keep'])}/mês.\n"
                        f"• +1 mês: {brl(s['plus_one'])}/mês; +2 meses: {brl(s['plus_two'])}/mês.\n"
                        f"• Outras metas ativas pedem {brl(s['other_goals'])}/mês.\n"
                        f"• Margem conservadora disponível para esta meta: {brl(s['free'])}.\n"
                        f"• Saldo projetado após contas: {brl(d['projected_balance'])}.\n\n"
                        f"🦉 Nex recomenda: {rec} Use ‘Simular aporte’ para testar uma entrada. Nenhum dinheiro foi movimentado.")

            if context.action == 'evaluate_acquisition' or any(k in q for k in ('aquisic','qual compra','qual item')):
                goals=scoped_goals()
                d = self.app.dashboard_data()
                if not self.app.cloud.online:
                    return 'Estou usando a última cópia offline. Sincronize antes de decidir uma compra; os compromissos podem ter mudado.'
                all_items=[item for item in self.app.cloud.list_acquisitions(True) if str(item.get('member_id') or '')==str(context.member_id)]
                selected=None
                if context.entity_id:
                    selected=next((x for x in all_items if str(x.get('id'))==context.entity_id),None)
                match = re.search(r'(?:até|ate|uns?|por|de)\s*(?:r\$\s*)?(\d[\d.]*(?:,\d{1,2})?)', text.lower())
                limit = self.app_money(match.group(1)) if match else None
                source_items=[selected] if selected else all_items
                rows, budget = affordable_acquisitions(
                    source_items, d, goals,
                    self.app.preferences.get('minimum_reserve',0), limit
                )
                if selected and not rows:
                    price=float(selected.get('estimated') or 0)
                    return (f"Eu esperaria para comprar {selected.get('item','esse item')}. O preço registrado é {brl(price)} e o orçamento conservador disponível agora é {brl(budget)}. "
                            "Esse cálculo considera saldo após compromissos, reserva protegida e esforço mensal das metas. Comissão/afiliado nunca entra nessa decisão.")
                if not rows:
                    return f'Eu esperaria. Nenhuma aquisição atende ao preço solicitado e ao orçamento conservador de {brl(budget)}. Fonte: perfil selecionado; comissão não participa do cálculo.'
                best = rows[0]
                return (f"{best['item']} ({brl(float(best['estimated']))}) cabe no orçamento conservador de {brl(budget)}. "
                        f"Fonte: aquisições, metas e caixa do perfil selecionado em {d['as_of']}. Antes de comprar, confira se a prioridade ainda faz sentido. A comissão não participa do cálculo.")

            if context.action == 'month_summary' or any(k in q for k in ('como esta meu mes','como está meu mês','resumo do mes','resumo do mês','meu mes ta suave','meu mês tá suave','to lascado esse mes','tô lascado esse mês')):
                d=self.app.dashboard_data()
                return (f"Resumo de {d.get('month', context.month)} — dados registrados até {d.get('as_of','agora')}.\n"
                        f"• Entraram {brl(d.get('income',0))}.\n"
                        f"• Saíram {brl(d.get('expense',0))} já efetivados.\n"
                        f"• Saldo atual do perfil: {brl(d.get('balance',0))}.\n"
                        f"• Próximos compromissos no período: {brl(d.get('pending_month',0))}.\n"
                        f"• Projetado após compromissos: {brl(d.get('projected_balance',0))}.\n"
                        "Se quiser, eu explico qual categoria mais pesou ou simulo uma decisão usando esses mesmos dados.")

            if context.action == 'next_bills' or 'proximas contas' in q or 'próximas contas' in q:
                d=self.app.dashboard_data()
                rows=d.get('pending_rows') or []
                if not rows:
                    return 'Não encontrei compromissos pendentes no período selecionado. Se alguma conta ainda não foi cadastrada, ela não entra nesta resposta.'
                parts=[]
                for row in rows[:5]:
                    parts.append(f"• {row.get('description') or row.get('category') or 'Conta'} — {brl(row.get('amount',0))} em {row.get('expense_date') or 'data não informada'}")
                return 'Próximas contas registradas:\n' + '\n'.join(parts) + f"\nTotal pendente no período: {brl(d.get('pending_month',0))}."

            if context.action == 'save_money' or 'me ajude a economizar' in q:
                analysis=self.app.financial_analysis()
                d=self.app.dashboard_data()
                cats=list(d.get('categories') or [])
                top=cats[0] if cats else None
                base=(f"Hoje eu começaria protegendo {brl(max(float(analysis.get('free_margin') or 0),0))} de margem conservadora antes de assumir gasto novo.")
                if top:
                    base += f" Seu maior grupo no período é {top[0]} ({brl(top[1])}); vale abrir os lançamentos dessa categoria e procurar cortes que não afetem o essencial."
                return base + ' Posso comparar uma categoria específica ou simular uma economia mensal sem alterar nenhum lançamento.'

            local_response = self.app.financial_chat_response(text)
            if not self._generic_local_response(local_response):
                return local_response
            if not online_attempted:
                try:
                    online_response = self._online_reply(text, context)
                    if online_response:
                        self.last_mode = "online"
                        return online_response
                except GatewayUnavailable as exc:
                    self.last_mode = "fallback"
                    self.connection_state="offline"
                    self.last_gateway_error=str(exc)
                    logger.info('nex_gateway_unavailable kind=%s', type(exc).__name__)
            if self._generic_local_response(local_response):
                self.last_mode = "fallback"
                return self._honest_general_fallback()
            return local_response
        except Exception as exc:
            logger.warning('nex_failed kind=%s', type(exc).__name__)
            return 'Não consegui consultar os dados agora. Não vou estimar valores. Tente novamente; sua pergunta ficou no histórico.'

    @staticmethod
    def app_money(value):
        return float(value.replace('.','').replace(',','.')) if ',' in value else float(value)
