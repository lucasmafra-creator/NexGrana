"""Fronteira única da conversa do Nex.

A camada conversacional interpreta a intenção, mas números financeiros críticos
vêm dos serviços determinísticos.  O cliente não contém chave de LLM e não
finge que há IA externa conectada quando não há backend configurado.
"""
from dataclasses import dataclass
import logging
import re
from .finance_engine import affordable_acquisitions, goal_scenarios

logger = logging.getLogger(__name__)


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


def brl(value):
    return f'R$ {value:,.2f}'.replace(',','X').replace('.',',').replace('X','.')


class NexEngine:
    def __init__(self, app):
        self.app = app

    def respond(self, text, context):
        try:
            if context.household_id != str(self.app.cloud._hid()):
                raise ValueError('Contexto alterado')
            if context.member_id and context.member_id not in {str(m.get('id')) for m in self.app.members()}:
                raise ValueError('Perfil fora da família')
            q = self.app._norm(text)

            if context.action == 'continue_journey':
                payload=context.payload or {}
                title=payload.get('title') or context.entity_id or 'sua trilha'
                steps=[
                    ('Escolher e validar a atividade','definir cliente, problema e um teste pequeno antes de investir'),
                    ('Avaliar sua situação','confirmar tempo, capital, habilidade, formato e recursos já disponíveis'),
                    ('Aprender o básico','separar o conhecimento mínimo e um material confiável para estudar'),
                    ('Calcular custos','listar material, taxa, deslocamento, tempo e perdas'),
                    ('Definir preço e margem','calcular preço mínimo e margem sem prometer faturamento'),
                    ('Buscar primeiros clientes','montar uma oferta pequena e testar com poucas pessoas'),
                    ('Registrar a primeira venda','registrar a receita real vinculada à atividade'),
                    ('Registrar custos e lucro','comparar receita e custos sem dupla contagem'),
                    ('Revisar o resultado','avaliar margem, horas, recorrência e feedback'),
                    ('Decidir se amplia','continuar, ajustar, pausar ou escalar com base no resultado real'),
                ]
                progress=max(0,min(int(payload.get('progress') or 0),len(steps)))
                if progress >= len(steps):
                    return (f'Sua Trilha Nex de {title} está concluída. Agora compare receita, custos, horas e recorrência antes de ampliar. '
                            'Se quiser, me diga o resultado registrado e eu ajudo a interpretar sem prometer ganho.')
                name,mission=steps[progress]
                return (f'Trilha Nex — {title}. Etapa {progress+1}/{len(steps)}: {name}.\n'
                        f'Próxima missão: {mission}.\n'
                        'Vamos fazer uma coisa por vez. Me diga o que já está pronto nessa etapa e eu continuo dali.')

            if context.action == 'simulate_goal' or ('simul' in q and 'meta' in q):
                goals = self.app.cloud.list_goals()
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
                d = self.app.dashboard_data()
                if not self.app.cloud.online:
                    return 'Estou usando a última cópia offline. Sincronize antes de decidir uma compra; os compromissos podem ter mudado.'
                all_items=self.app.cloud.list_acquisitions(True)
                selected=None
                if context.entity_id:
                    selected=next((x for x in all_items if str(x.get('id'))==context.entity_id),None)
                match = re.search(r'(?:até|ate|uns?|por|de)\s*(?:r\$\s*)?(\d[\d.]*(?:,\d{1,2})?)', text.lower())
                limit = self.app_money(match.group(1)) if match else None
                source_items=[selected] if selected else all_items
                rows, budget = affordable_acquisitions(
                    source_items, d, self.app.cloud.list_goals(),
                    self.app.preferences.get('minimum_reserve',0), limit
                )
                if selected and not rows:
                    price=float(selected.get('estimated') or 0)
                    return (f"Eu esperaria para comprar {selected.get('item','esse item')}. O preço registrado é {brl(price)} e o orçamento conservador disponível agora é {brl(budget)}. "
                            "Esse cálculo considera saldo após compromissos, reserva protegida e esforço mensal das metas. Comissão/afiliado nunca entra nessa decisão.")
                if not rows:
                    return f'Eu esperaria. Nenhuma aquisição atende ao preço solicitado e ao orçamento conservador de {brl(budget)}. Fonte: registros da família; comissão não participa do cálculo.'
                best = rows[0]
                return (f"{best['item']} ({brl(float(best['estimated']))}) cabe no orçamento conservador de {brl(budget)}. "
                        f"Fonte: aquisições, metas e caixa da família em {d['as_of']}. Antes de comprar, confira se a prioridade ainda faz sentido. A comissão não participa do cálculo.")

            if context.action == 'month_summary' or any(k in q for k in ('como esta meu mes','como está meu mês','resumo do mes','resumo do mês')):
                d=self.app.dashboard_data()
                return (f"Resumo de {d.get('month', context.month)} — dados registrados até {d.get('as_of','agora')}.\n"
                        f"• Entraram {brl(d.get('income',0))}.\n"
                        f"• Saíram {brl(d.get('expense',0))} já efetivados.\n"
                        f"• Caixa acumulado disponível: {brl(d.get('balance',0))}.\n"
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

            return self.app.financial_chat_response(text)
        except Exception as exc:
            logger.warning('nex_failed kind=%s', type(exc).__name__)
            return 'Não consegui consultar os dados agora. Não vou estimar valores. Tente novamente; sua pergunta ficou no histórico.'

    @staticmethod
    def app_money(value):
        return float(value.replace('.','').replace(',','.')) if ',' in value else float(value)
