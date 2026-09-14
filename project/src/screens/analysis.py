from ui.common import (
    add_months,
    calendar,
    date,
    datetime,
    analysis_summary,
    base_desc,
    brl,
    defaultdict,
    ft,
    money,
    month_label,
    snapshot,
)


class AnalysisScreen:
    """Diagnóstico financeiro orientado a decisão, não a dashboard."""

    def assistant_screen(self):
        a = self.financial_analysis()
        phone = self._layout_bucket() == "phone"

        health_icon = {
            "good": "🟢",
            "attention": "🟡",
            "tight": "🟠",
            "critical": "🔴",
            "unknown": "⚪",
        }.get(a.get("health_level"), "⚪")

        flow = ft.Container(
            padding=14,
            bgcolor=self.surface_color(),
            border_radius=18,
            border=ft.Border.all(1, self.border_color()),
            content=ft.ResponsiveRow(
                spacing=8,
                run_spacing=8,
                controls=[
                    self._analysis_metric("Entrou", brl(a["income"]), "Renda efetivamente recebida", ft.Icons.SOUTH_WEST, ft.Colors.GREEN, phone),
                    self._analysis_metric("Saiu", brl(a["paid_expense"]), "Gastos já efetivados", ft.Icons.NORTH_EAST, ft.Colors.RED, phone),
                    self._analysis_metric("Ainda vence", brl(a["pending_expense"]), "Compromissos futuros do mês", ft.Icons.EVENT, ft.Colors.ORANGE, phone),
                    self._analysis_metric("Seguro para decidir", brl(a["safe_margin"]), "Após contas, reserva e esforço mensal das metas", ft.Icons.SHIELD_OUTLINED, "#8B7CFF", phone),
                ],
            ),
        )

        allocation = []
        for item in a["allocation"]:
            allocation.append(
                ft.Container(
                    padding=10,
                    border_radius=12,
                    bgcolor=self.surface_alt_color(),
                    content=ft.Column(
                        spacing=5,
                        controls=[
                            ft.Row(
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                controls=[
                                    ft.Text(item["label"], weight=ft.FontWeight.BOLD),
                                    ft.Text(f"{item['percent']:.0f}% • {brl(item['amount'])}", weight=ft.FontWeight.BOLD),
                                ],
                            ),
                            ft.ProgressBar(value=max(0, min(item["percent"] / 100, 1)), color=item["color"]),
                        ],
                    ),
                )
            )

        action_cards = []
        for item in a["actions"][:8]:
            action_cards.append(
                ft.Container(
                    padding=14,
                    bgcolor=self.surface_color(),
                    border_radius=16,
                    border=ft.Border.all(1, self.border_color()),
                    content=ft.Row(
                        vertical_alignment=ft.CrossAxisAlignment.START,
                        controls=[
                            ft.Text(item["icon"], size=26),
                            ft.Column(
                                expand=True,
                                spacing=5,
                                controls=[
                                    ft.Text(item["title"], weight=ft.FontWeight.BOLD, size=14),
                                    ft.Text(item["text"], size=11, color=self.muted_color()),
                                    ft.Text(item["impact"], size=10, color=ft.Colors.GREEN_400, weight=ft.FontWeight.BOLD)
                                    if item.get("impact")
                                    else ft.Container(),
                                    ft.Row(
                                        wrap=True,
                                        spacing=4,
                                        controls=[
                                            ft.TextButton(
                                                "Entender com o Nex",
                                                icon=ft.Icons.AUTO_AWESOME,
                                                on_click=lambda e, t=item["title"]: self._start_nex_topic(
                                                    "Me explique esta prioridade da minha análise: " + t,
                                                    source="analysis",
                                                ),
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                )
            )

        comparison_text = a.get("comparison_text") or "Ainda não há mês anterior suficiente para comparar."
        hero = ft.Container(
            padding=18,
            border_radius=20,
            bgcolor="#17192B" if self.is_dark() else "#F4F2FF",
            border=ft.Border.all(1, "#393266"),
            content=ft.ResponsiveRow(
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Container(
                        col={"xs": 12, "sm": 8},
                        content=ft.Column(
                            spacing=7,
                            controls=[
                                ft.Text(f"{health_icon} Seu mês está {a['health'].lower()}", size=22, weight=ft.FontWeight.BOLD),
                                ft.Text(a["health_detail"], size=12, color=self.muted_color()),
                                ft.Text(comparison_text, size=11, color="#A99CFF"),
                                ft.Row(
                                    wrap=True,
                                    controls=[
                                        ft.Button(
                                            "Montar meu plano",
                                            icon=ft.Icons.AUTO_AWESOME,
                                            on_click=lambda e: self._start_nex_topic(
                                                "Com base na minha análise atual, monte um plano prático para o restante do mês.",
                                                source="analysis_plan",
                                            ),
                                        ),
                                        ft.TextButton("Editar divisão", on_click=lambda e: self.allocation_dialog()),
                                    ],
                                ),
                            ],
                        ),
                    ),
                    ft.Container(
                        col={"xs": 12, "sm": 4},
                        alignment=ft.Alignment.CENTER,
                        content=ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=2,
                            controls=[
                                ft.Text("Margem segura", size=10, color=self.muted_color()),
                                ft.Text(brl(a["safe_margin"]), size=26, weight=ft.FontWeight.BOLD, color="#A99CFF"),
                                ft.Text("referência conservadora", size=9, color=self.subtle_color()),
                            ],
                        ),
                    ),
                ],
            ),
        )

        return ft.Column(
            expand=True,
            controls=[
                self.header("Análises", "Entenda o mês e escolha o próximo passo"),
                ft.Container(
                    padding=12 if phone else 16,
                    expand=True,
                    content=ft.Column(
                        scroll=ft.ScrollMode.ALWAYS,
                        spacing=12,
                        controls=[
                            hero,
                            flow,
                            ft.Container(
                                padding=15,
                                bgcolor=self.surface_color(),
                                border_radius=16,
                                border=ft.Border.all(1, self.border_color()),
                                content=ft.Column(
                                    spacing=8,
                                    controls=[
                                        ft.Text("🦉 O Nex faria isso com a margem segura", size=17, weight=ft.FontWeight.BOLD),
                                        ft.Text(
                                            "É uma simulação editável. Nada é movimentado automaticamente e a divisão se adapta aos compromissos registrados.",
                                            size=10,
                                            color=self.muted_color(),
                                        ),
                                        *allocation,
                                    ],
                                ),
                            ),
                            ft.Text("O que merece sua atenção", size=17, weight=ft.FontWeight.BOLD),
                            *action_cards,
                            ft.Text(
                                "As sugestões usam registros da família e exemplos de redução; não tratam gasto hipotético como economia garantida.",
                                size=10,
                                color=self.subtle_color(),
                            ),
                        ],
                    ),
                ),
            ],
        )

    def _analysis_metric(self, title, value, subtitle, icon, color, phone):
        return ft.Container(
            col={"xs": 6, "md": 3},
            padding=12,
            border_radius=14,
            bgcolor=self.surface_alt_color(),
            content=ft.Column(
                spacing=4,
                controls=[
                    ft.Icon(icon, color=color, size=19),
                    ft.Text(title, size=10, color=self.muted_color()),
                    ft.Text(value, size=17 if phone else 19, weight=ft.FontWeight.BOLD),
                    ft.Text(subtitle, size=8 if phone else 9, color=self.subtle_color()),
                ],
            ),
        )

    def financial_analysis(self):
        current = self.dashboard_data()
        goals = self.cloud.list_goals() or []
        percentages = self.preferences.get("allocation", [40, 30, 10, 20])
        summary = analysis_summary(
            current,
            goals,
            percentages,
            self.preferences.get("minimum_reserve", 0),
        )
        color_map = {
            "good": ft.Colors.GREEN,
            "attention": ft.Colors.ORANGE,
            "tight": ft.Colors.DEEP_ORANGE,
            "critical": ft.Colors.RED,
            "unknown": ft.Colors.GREY,
        }
        summary["health_color"] = color_map.get(summary["health_level"], ft.Colors.GREY)

        all_exp = self.cloud.all_expenses(limit=5000)
        next_month = add_months(self.month, 1)
        next_month_installments = 0.0
        total_future = 0.0
        grouped_current = defaultdict(lambda: {"count": 0, "total": 0.0, "category": ""})
        current_idx = int(self.month[3:]) * 12 + int(self.month[:2])

        for x in all_exp:
            if x.get("payment_status") == "cancelled":
                continue
            try:
                idx = int(x["month"][3:]) * 12 + int(x["month"][:2])
            except (ValueError, TypeError, KeyError):
                continue
            if int(x.get("installments_total") or 1) > 1:
                if x.get("month") == next_month:
                    next_month_installments += float(x["amount"])
                if idx > current_idx:
                    total_future += float(x["amount"])
            if x.get("month") == self.month:
                key = base_desc(x["description"])
                grouped_current[key]["count"] += 1
                grouped_current[key]["total"] += float(x["amount"])
                grouped_current[key]["category"] = x.get("category") or "Outros"

        actions = []
        rules = {
            "delivery": (20, "Compare frequência e defina um teto semanal."),
            "lanche": (15, "Planejar parte dos lanches pode reduzir repetição."),
            "streaming": (25, "Revise plataformas pouco utilizadas."),
            "assinatura": (25, "Cancele ou pause assinaturas sem uso."),
            "uber": (10, "Compare deslocamentos recorrentes quando houver alternativa."),
        }
        for desc, info in sorted(grouped_current.items(), key=lambda kv: kv[1]["total"], reverse=True):
            matched = None
            for term, (pct, advice) in rules.items():
                if term in desc:
                    matched = (pct, advice)
                    break
            if not matched and info["count"] >= 4:
                matched = (10, "Esse gasto apareceu várias vezes no mês; vale revisar a frequência.")
            if matched:
                pct, advice = matched
                reduc = info["total"] * pct / 100
                actions.append(
                    {
                        "icon": "💡",
                        "title": desc.title(),
                        "text": f"{info['count']} lançamento(s), total {brl(info['total'])}. {advice}",
                        "impact": f"Simulação de redução de {pct}%: {brl(reduc)} — não é economia garantida.",
                    }
                )

        if next_month_installments > 0:
            actions.insert(
                0,
                {
                    "icon": "📅",
                    "title": "Parcelas chegando",
                    "text": f"Há {brl(next_month_installments)} em parcelas já registradas para {month_label(next_month)}.",
                    "impact": f"Parcelas de todos os meses futuros: {brl(total_future)}.",
                },
            )
        if summary["goal_monthly_commitment"] > 0:
            actions.insert(
                0,
                {
                    "icon": "🎯",
                    "title": "Metas também consomem margem",
                    "text": f"As metas ativas pedem aproximadamente {brl(summary['goal_monthly_commitment'])}/mês no ritmo atual.",
                    "impact": "Esse valor é esforço futuro; dinheiro já guardado não é descontado duas vezes.",
                },
            )
        if summary["safe_margin"] > 0:
            actions.insert(
                0,
                {
                    "icon": "🛟",
                    "title": "Margem segura para decidir",
                    "text": f"Depois de contas, reserva protegida e metas, a referência conservadora é {brl(summary['safe_margin'])}.",
                    "impact": "Use como limite de decisão, não como obrigação de gastar.",
                },
            )
        if not actions:
            actions = [
                {
                    "icon": "✅",
                    "title": "Sem alerta forte neste mês",
                    "text": "Ainda não há padrão suficiente para sugerir cortes rastreáveis. Continue registrando os gastos.",
                    "impact": "",
                }
            ]

        labels = ["Reserva", "Metas", "Lazer", "Manter livre"]
        palette = [ft.Colors.GREEN, ft.Colors.PURPLE, ft.Colors.ORANGE, ft.Colors.BLUE]
        summary["allocation"] = [
            {"label": label, "percent": pct, "amount": val, "color": color}
            for label, pct, val, color in zip(
                labels,
                summary["allocation_percentages"],
                summary["allocation_amounts"],
                palette,
            )
        ]

        try:
            previous_month = add_months(self.month, -1)
            pm,py=map(int,previous_month.split("/"))
            now=date.today()
            selected_is_current=self.month==now.strftime("%m/%Y")
            comparable_today=None
            comparison_suffix=""
            if selected_is_current:
                comparable_today=date(py,pm,min(now.day,calendar.monthrange(py,pm)[1]))
                comparison_suffix=f" até o dia {comparable_today.day}"
            previous = snapshot(
                self.cloud.all_income(limit=5000),
                self.cloud.all_expenses_full(limit=5000),
                previous_month,
                self.members(),
                today=comparable_today,
            )
            prev_spend = float(previous.get("expense") or 0)
            now_spend = float(current.get("expense") or 0)
            if prev_spend > 0:
                diff = now_spend - prev_spend
                pct = abs(diff) / prev_spend * 100
                direction = "mais" if diff > 0 else "menos"
                summary["comparison_text"] = f"Você gastou {pct:.0f}% {direction} que em {month_label(previous_month)}{comparison_suffix} ({brl(abs(diff))} de diferença)."
            else:
                summary["comparison_text"] = f"{month_label(previous_month)}{comparison_suffix} ainda não tem gastos pagos suficientes para comparação."
        except Exception:
            summary["comparison_text"] = "Comparação com o mês anterior indisponível agora."

        summary.update(
            next_month_installments=next_month_installments,
            future_installments=total_future,
            actions=actions,
        )
        return summary

    def allocation_dialog(self):
        labels = ["Reserva", "Metas", "Lazer", "Manter livre"]
        values = self.preferences.get("allocation", [40, 30, 10, 20])
        fields = [
            ft.TextField(label=label + " (%)", value=str(value), keyboard_type=ft.KeyboardType.NUMBER)
            for label, value in zip(labels, values)
        ]
        reserve = ft.TextField(
            label="Reserva mínima protegida (R$)",
            value=str(self.preferences.get("minimum_reserve", 0)),
        )
        d = ft.AlertDialog(
            title=ft.Text("Sua divisão da margem"),
            content=ft.Column(tight=True, scroll=ft.ScrollMode.AUTO, controls=fields + [reserve]),
        )

        def save(e):
            try:
                numbers = [money(f.value) for f in fields]
                if any(n < 0 for n in numbers) or abs(sum(numbers) - 100) > 0.001:
                    raise ValueError("A soma deve ser 100%.")
                floor = money(reserve.value)
                if floor < 0:
                    raise ValueError("Reserva não pode ser negativa.")
                self.preferences.update(allocation=numbers, minimum_reserve=floor)
                self.save_preferences()
                self.page.pop_dialog()
                self.render()
            except ValueError as exc:
                self.snack(str(exc), True)

        d.actions = [
            ft.TextButton("Cancelar", on_click=lambda e: self.page.pop_dialog()),
            ft.Button("Salvar", on_click=save),
        ]
        self.page.show_dialog(d)
