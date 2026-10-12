from ui.common import FINANCIAL_RESOURCES, brl, ft, money
from services.investment_engine import investment_projection


class InvestmentsScreen:
    """Educação e simulação: nunca cotação, promessa ou ordem de investimento."""

    def investment_simulator_dialog(self, e=None):
        initial = ft.TextField(label="Valor inicial", value="0", keyboard_type=ft.KeyboardType.NUMBER)
        monthly = ft.TextField(label="Aporte mensal", value="100", keyboard_type=ft.KeyboardType.NUMBER)
        months = ft.TextField(label="Prazo em meses", value="12", keyboard_type=ft.KeyboardType.NUMBER)
        rate = ft.TextField(label="Taxa hipotética (%)", value="0,5", keyboard_type=ft.KeyboardType.NUMBER)
        rate_period = ft.Dropdown(
            label="Periodicidade da taxa",
            value="monthly",
            options=[ft.DropdownOption(key="monthly", text="Mensal"), ft.DropdownOption(key="annual", text="Anual efetiva")],
        )
        contribution_timing = ft.Dropdown(
            label="Momento do aporte",
            value="end",
            options=[ft.DropdownOption(key="end", text="Fim de cada mês"), ft.DropdownOption(key="begin", text="Início de cada mês")],
        )
        costs = ft.TextField(label="Custos totais informados (opcional)", value="0", keyboard_type=ft.KeyboardType.NUMBER)
        taxes = ft.TextField(label="Impostos totais informados (opcional)", value="0", keyboard_type=ft.KeyboardType.NUMBER)
        result = ft.Text("Preencha os campos e toque em Simular.", selectable=True)

        def simulate(_):
            try:
                projection = investment_projection(
                    money(initial.value or "0"),
                    money(monthly.value or "0"),
                    int(months.value or 0),
                    (rate.value or "0").replace(".", "").replace(",", "."),
                    rate_period=rate_period.value,
                    contribution_timing=contribution_timing.value,
                    costs=money(costs.value or "0"),
                    taxes=money(taxes.value or "0"),
                )
                timing = "início" if projection["contribution_timing"] == "begin" else "fim"
                result.value = (
                    f"Resultado bruto simulado: {brl(float(projection['gross_result']))}.\n"
                    f"Total aportado: {brl(float(projection['total_invested']))}.\n"
                    f"Ganho/perda hipotético: {brl(float(projection['hypothetical_gain']))}.\n"
                    f"Custos informados: {brl(float(projection['costs']))}; impostos informados: {brl(float(projection['taxes']))}.\n"
                    f"Resultado líquido matemático: {brl(float(projection['net_result']))}.\n\n"
                    f"Premissas: {projection['periods']} meses, aporte no {timing} do mês e {projection['convention']}. "
                    "A taxa, custos e impostos vieram de você. Isto não é previsão, cotação ou recomendação e não altera seu saldo."
                )
                result.update()
            except (ValueError, TypeError):
                self.snack("Revise os valores da simulação.", True)

        dialog = ft.AlertDialog(
            title=ft.Text("Simulador educacional"),
            content=ft.Column(width=520, tight=True, scroll=ft.ScrollMode.AUTO, controls=[
                ft.Text("Compare cenários sem movimentar dinheiro e sem usar rentabilidade inventada.", size=10, color=self.muted_color()),
                initial, monthly, months, rate,
                ft.ResponsiveRow(spacing=8, run_spacing=8, controls=[
                    ft.Container(col={"xs":12,"sm":6}, content=rate_period),
                    ft.Container(col={"xs":12,"sm":6}, content=contribution_timing),
                    ft.Container(col={"xs":12,"sm":6}, content=costs),
                    ft.Container(col={"xs":12,"sm":6}, content=taxes),
                ]),
                result,
            ]),
            actions=[
                ft.TextButton("Fechar", on_click=lambda event: self.page.pop_dialog()),
                ft.Button("Simular", icon=ft.Icons.CALCULATE_OUTLINED, on_click=simulate),
            ],
        )
        self.page.show_dialog(dialog)

    def investments_screen(self):
        profile = (self.active_member() or {}).get("display_name") or "você"
        cards = [
            ("1", "Objetivo e prazo", "Defina para que serve o dinheiro e quando ele será usado."),
            ("2", "Reserva primeiro", "Dinheiro de emergência pede segurança e acesso rápido, não promessa de maior retorno."),
            ("3", "Entenda o risco", "Compare liquidez, risco de crédito e mercado, custos, impostos e diversificação."),
            ("4", "Decida conscientemente", "Confirme informações em fonte oficial antes de aplicar em qualquer produto."),
        ]
        steps = [ft.Container(
            col={"xs": 12, "md": 6}, padding=14, border_radius=16,
            bgcolor=self.surface_color(), border=ft.Border.all(1, self.border_color()),
            content=ft.Row(vertical_alignment=ft.CrossAxisAlignment.START, controls=[
                ft.Container(width=34, height=34, border_radius=17, alignment=ft.Alignment.CENTER, bgcolor="#2D3563", content=ft.Text(number, weight=ft.FontWeight.BOLD)),
                ft.Column(expand=True, spacing=3, controls=[ft.Text(title, weight=ft.FontWeight.BOLD), ft.Text(text, size=10, color=self.muted_color())]),
            ]),
        ) for number, title, text in cards]
        sources = [ft.ListTile(
            leading=ft.Icon(ft.Icons.VERIFIED_OUTLINED, color="#8B7CFF"),
            title=ft.Text(item["title"], size=12, weight=ft.FontWeight.BOLD),
            subtitle=ft.Text(item["subtitle"], size=9),
            trailing=ft.Icon(ft.Icons.OPEN_IN_NEW, size=16),
            on_click=lambda event, url=item["url"]: self.page.run_task(self.open_external_url, url),
        ) for item in FINANCIAL_RESOURCES]
        return ft.Column(expand=True, controls=[
            self.header("Investimentos", "Aprenda, compare cenários e decida sem promessas"),
            ft.Container(padding=16, expand=True, content=ft.Column(scroll=ft.ScrollMode.ALWAYS, spacing=12, controls=[
                ft.Container(padding=16, border_radius=18, bgcolor=self.surface_alt_color(), border=ft.Border.all(1, self.border_color()), content=ft.ResponsiveRow(vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                    ft.Container(col={"xs": 9, "md": 10}, content=ft.Column(spacing=5, controls=[
                        ft.Text(f"Base de decisão de {profile}", size=18, weight=ft.FontWeight.BOLD),
                        ft.Text("O Nex explica conceitos e usa apenas seus registros para contextualizar. Ele não indica ativo específico, não busca cotação em tempo real e não garante retorno.", size=10, color=self.muted_color()),
                        ft.Row(wrap=True, controls=[
                            ft.Button("Simular cenário", icon=ft.Icons.CALCULATE_OUTLINED, on_click=self.investment_simulator_dialog),
                            ft.OutlinedButton("Conversar com o Nex", icon=ft.Icons.AUTO_AWESOME, on_click=lambda event: self._start_nex_topic("Quero aprender sobre investimentos considerando meu objetivo, prazo, liquidez e tolerância a risco.", source="investments", action="investment_education")),
                        ]),
                    ])),
                    ft.Container(col={"xs": 3, "md": 2}, alignment=ft.Alignment.CENTER, content=ft.Image(src=self.nex_asset("thinking", "card", context="investments"), width=100, height=100, fit=ft.BoxFit.CONTAIN)),
                ])),
                ft.Text("Caminho limpo para começar", size=16, weight=ft.FontWeight.BOLD),
                ft.ResponsiveRow(spacing=8, run_spacing=8, controls=steps),
                ft.Text("Fontes públicas para conferir", size=16, weight=ft.FontWeight.BOLD),
                ft.Container(border_radius=16, bgcolor=self.surface_color(), content=ft.Column(spacing=0, controls=sources)),
                ft.Text("Conteúdo educacional. Investimentos envolvem riscos e podem gerar perdas.", size=9, color=self.subtle_color()),
            ])),
        ])
