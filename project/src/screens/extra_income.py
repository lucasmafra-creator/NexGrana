from ui.common import EXTRA_INCOME_MANUALS, datetime, ft, re, money, brl


class ExtraIncomeScreen:
    JOURNEY_STEPS = [
        ("Escolher e validar a atividade", "Cliente, problema e um teste pequeno antes de investir."),
        ("Avaliar sua situação", "Tempo, capital, habilidades, formato e recursos disponíveis."),
        ("Aprender o básico", "Conhecimento mínimo antes de gastar dinheiro."),
        ("Calcular custos", "Materiais, deslocamento, tempo, taxas e perdas."),
        ("Definir preço e margem", "Preço que cubra custos e gere lucro real."),
        ("Buscar os primeiros clientes", "Teste pequeno antes de aumentar investimento."),
        ("Registrar a primeira venda", "Receita real vinculada à atividade."),
        ("Registrar custos e lucro", "Separar custos reais e evitar dupla contagem."),
        ("Revisar o resultado", "Margem, horas, recorrência e feedback."),
        ("Decidir se amplia", "Continuar, ajustar, pausar ou escalar com base nos dados."),
    ]

    def _journey_record(self, title):
        return next((r for r in self.extra_income_journeys if r.get("title") == title), {})

    def _refresh_journeys(self):
        self.extra_income_journeys = self.cloud.list_journeys(self.active_member_id)
        self.extra_income_path = self.cloud.load_journey_progress(self.active_member_id)

    def extra_income_path_dialog(self, title, meta, guide):
        record = self._journey_record(title)
        progress = int(record.get("progress") or self.extra_income_path.get(title, 0) or 0)
        status = record.get("status") or "active"
        reminder_enabled = bool(record.get("reminder_enabled"))
        reminder_days = list(record.get("reminder_days") or [])
        reminder_at = str(record.get("reminder_at") or "")
        reminder_time = "19:00"
        m = re.search(r"T(\d{2}:\d{2})", reminder_at)
        if m:
            reminder_time = m.group(1)

        rows = []
        for i, (name, desc) in enumerate(self.JOURNEY_STEPS):
            done = i < progress
            current = i == progress and status == "active"
            rows.append(
                ft.Container(
                    padding=9,
                    border_radius=12,
                    bgcolor=self.surface_alt_color() if current else None,
                    content=ft.ListTile(
                        leading=ft.Icon(
                            ft.Icons.CHECK_CIRCLE if done else (ft.Icons.PLAY_CIRCLE_OUTLINE if current else ft.Icons.RADIO_BUTTON_UNCHECKED),
                            color=ft.Colors.GREEN if done else "#8B7CFF",
                        ),
                        title=ft.Text(f"{i + 1}. {name}", weight=ft.FontWeight.BOLD if current else None),
                        subtitle=ft.Text(desc, size=10),
                        on_click=lambda e, idx=i: self._set_extra_income_progress(title, idx + 1),
                    ),
                )
            )

        metrics=dict(record.get("metrics") or {})
        notes_field=ft.TextField(label="Notas da trilha",value=str(metrics.get("notes") or ""),multiline=True,min_lines=2,max_lines=4)
        expected_cost=ft.TextField(label="Custo previsto (anotação)",value=str(metrics.get("expected_cost") or "").replace(".",","),keyboard_type=ft.KeyboardType.NUMBER)
        actual_cost=ft.TextField(label="Custo real (anotação)",value=str(metrics.get("actual_cost") or "").replace(".",","),keyboard_type=ft.KeyboardType.NUMBER)
        revenue_note=ft.TextField(label="Receita observada (anotação)",value=str(metrics.get("revenue_note") or "").replace(".",","),keyboard_type=ft.KeyboardType.NUMBER)
        hours_note=ft.TextField(label="Horas dedicadas",value=str(metrics.get("hours") or "").replace(".",","),keyboard_type=ft.KeyboardType.NUMBER)
        reminder_switch = ft.Switch(label="Nex me lembra dentro do app", value=reminder_enabled)
        time_field = ft.TextField(label="Horário", value=reminder_time, width=130, hint_text="19:00")
        day_boxes = []
        day_labels = [(1, "Seg"), (2, "Ter"), (3, "Qua"), (4, "Qui"), (5, "Sex"), (6, "Sáb"), (7, "Dom")]
        for n, label in day_labels:
            day_boxes.append(ft.Checkbox(label=label, value=n in reminder_days, data=n))

        def save_reminder(e):
            try:
                raw=(time_field.value or "").strip()
                if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", raw):
                    raise ValueError("Use horário no formato HH:MM.")
                days=[int(c.data) for c in day_boxes if c.value]
                if reminder_switch.value and not days:
                    raise ValueError("Escolha pelo menos um dia para o lembrete.")
                # Armazenamos uma âncora ISO; o aviso desta versão é exibido ao abrir
                # o app, não é push do sistema operacional.
                anchor=datetime.now().replace(hour=int(raw[:2]),minute=int(raw[3:]),second=0,microsecond=0).isoformat()
                self.cloud.save_journey_progress(
                    title,
                    progress,
                    member_id=self.active_member_id,
                    status=status,
                    reminder_enabled=bool(reminder_switch.value),
                    reminder_days=days,
                    reminder_at=anchor,
                    metrics={"reminder_mode":"in_app","reminder_time":raw},
                )
                try:
                    self.cloud.set_privacy_consent("reminders", bool(reminder_switch.value))
                except Exception:
                    pass
                self._refresh_journeys()
                self.snack("Acompanhamento da Trilha Nex atualizado.")
            except ValueError as exc:
                self.snack(str(exc), True)
            except Exception:
                self.snack("Não consegui salvar o lembrete agora.", True)

        def save_metrics(e):
            try:
                def optional_money(field):
                    raw=(field.value or "").strip()
                    return None if not raw else money(raw)
                hours_raw=(hours_note.value or "").strip()
                hours=float(hours_raw.replace(",",".")) if hours_raw else None
                if hours is not None and hours < 0:
                    raise ValueError("Horas não podem ser negativas.")
                new_metrics={
                    "notes":(notes_field.value or "").strip(),
                    "expected_cost":optional_money(expected_cost),
                    "actual_cost":optional_money(actual_cost),
                    "revenue_note":optional_money(revenue_note),
                    "hours":hours,
                }
                for k,v in new_metrics.items():
                    if isinstance(v,(int,float)) and v < 0:
                        raise ValueError("Valores da trilha não podem ser negativos.")
                self.cloud.save_journey_progress(title,progress,member_id=self.active_member_id,status=status,metrics=new_metrics)
                self._refresh_journeys()
                self.snack("Acompanhamento da trilha salvo. Essas anotações não criam lançamentos financeiros.")
            except ValueError as exc:
                self.snack(str(exc),True)
            except Exception:
                self.snack("Não consegui salvar as anotações da trilha agora.",True)

        def toggle_status(e):
            new_status = "active" if status == "paused" else "paused"
            try:
                self.cloud.save_journey_progress(
                    title,
                    progress,
                    member_id=self.active_member_id,
                    status=new_status,
                )
                self._refresh_journeys()
                self.page.pop_dialog()
                self.extra_income_path_dialog(title, meta, guide)
            except Exception:
                self.snack("Não consegui alterar o estado da trilha.", True)

        next_name = self.JOURNEY_STEPS[min(progress, len(self.JOURNEY_STEPS)-1)][0]
        dialog_w, dialog_h = self.dialog_dimensions(620, 620)
        d = ft.AlertDialog(
            title=ft.Text(f"Trilha Nex — {title}"),
            content=ft.Column(
                width=dialog_w,
                height=dialog_h,
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    ft.Text(meta, weight=ft.FontWeight.BOLD, color="#9A8BFF"),
                    ft.Text(guide, size=11, color=self.muted_color()),
                    ft.Row(
                        wrap=True,
                        controls=[
                            ft.Container(
                                padding=8,
                                border_radius=12,
                                bgcolor="#24213F",
                                content=ft.Text(f"{int(progress/len(self.JOURNEY_STEPS)*100)}% concluído", size=10, weight=ft.FontWeight.BOLD),
                            ),
                            ft.Container(
                                padding=8,
                                border_radius=12,
                                bgcolor="#24213F",
                                content=ft.Text("Pausada" if status == "paused" else f"Próxima: {next_name}", size=10),
                            ),
                        ],
                    ),
                    ft.ProgressBar(value=min(progress/len(self.JOURNEY_STEPS),1), color="#7C5CFF"),
                    *rows,
                    ft.Divider(),
                    ft.Text("Meu acompanhamento",size=15,weight=ft.FontWeight.BOLD),
                    ft.Text("Anotações de estudo/resultado. Não viram receita ou despesa automaticamente.",size=10,color=self.muted_color()),
                    notes_field,
                    ft.ResponsiveRow(spacing=8,run_spacing=8,controls=[
                        ft.Container(col={"xs":12,"sm":6},content=expected_cost),
                        ft.Container(col={"xs":12,"sm":6},content=actual_cost),
                        ft.Container(col={"xs":12,"sm":6},content=revenue_note),
                        ft.Container(col={"xs":12,"sm":6},content=hours_note),
                    ]),
                    ft.Button("Salvar acompanhamento",icon=ft.Icons.SAVE_OUTLINED,on_click=save_metrics),
                    ft.Divider(),
                    ft.Text("Acompanhamento do Nex", size=15, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        "Lembrete opt-in dentro do app. Nesta versão ele aparece quando você abre o NexGrana; não é notificação push do Android/Windows.",
                        size=10,
                        color=self.muted_color(),
                    ),
                    reminder_switch,
                    ft.Row(wrap=True, controls=[time_field, *day_boxes]),
                    ft.Row(
                        wrap=True,
                        controls=[
                            ft.Button("Salvar acompanhamento", icon=ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED, on_click=save_reminder),
                            ft.OutlinedButton("Retomar trilha" if status == "paused" else "Pausar trilha", icon=ft.Icons.PAUSE_CIRCLE_OUTLINE, on_click=toggle_status),
                        ],
                    ),
                    ft.Divider(),
                    ft.OutlinedButton(
                        "▶ Vídeos para se aprofundar",
                        icon=ft.Icons.PLAY_CIRCLE_OUTLINE,
                        on_click=lambda e, url="https://www.youtube.com/@sebrae/videos": self.page.run_task(self.open_external_url, url),
                    ),
                    ft.Button(
                        "Conversar com o Nex sobre esta trilha",
                        icon=ft.Icons.AUTO_AWESOME,
                        on_click=lambda e, t=title: self._start_nex_topic(
                            f"Quero continuar minha Trilha Nex de {t}. Estou na etapa {min(progress+1,len(self.JOURNEY_STEPS))} de {len(self.JOURNEY_STEPS)}. Me ajude a executar a próxima missão.",
                            source="journey",
                            entity_id=title,
                            action="continue_journey",
                            payload={"title": title, "progress": progress, "status": status},
                        ),
                    ),
                ],
            ),
            actions=[ft.TextButton("Fechar", on_click=lambda e: self.page.pop_dialog())],
        )
        self.page.show_dialog(d)

    def _set_extra_income_progress(self, title, value):
        try:
            self.cloud.save_journey_progress(title, int(value), member_id=self.active_member_id, status="completed" if int(value) >= len(self.JOURNEY_STEPS) else "active")
            self._refresh_journeys()
            self.page.pop_dialog()
            for t, m, g in EXTRA_INCOME_MANUALS:
                if t == title:
                    self.extra_income_path_dialog(t, m, g)
                    break
        except Exception:
            self.snack("Não consegui registrar o progresso da trilha agora.", True)

    def extra_income_screen(self):
        active_records=[r for r in self.extra_income_journeys if (r.get("status") or "active") != "completed"]
        journey=[]
        for record in active_records[:4]:
            title=record.get("title") or "Trilha"
            progress=int(record.get("progress") or 0)
            paused=record.get("status") == "paused"
            reminder=" • 🔔 acompanhamento ativo" if record.get("reminder_enabled") else ""
            journey.append(
                ft.Container(
                    padding=12,
                    border_radius=16,
                    bgcolor=self.surface_alt_color(),
                    border=ft.Border.all(1,self.border_color()),
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.ROUTE, color="#8B7CFF"),
                            ft.Column(
                                expand=True,
                                spacing=4,
                                controls=[
                                    ft.Text(title, weight=ft.FontWeight.BOLD),
                                    ft.ProgressBar(value=min(progress/len(self.JOURNEY_STEPS),1), color="#7C5CFF"),
                                    ft.Text(
                                        ("Pausada" if paused else f"Etapa {min(progress+1,len(self.JOURNEY_STEPS))} de {len(self.JOURNEY_STEPS)}") + f" • {int(progress/len(self.JOURNEY_STEPS)*100)}%{reminder}",
                                        size=9,
                                        color=self.muted_color(),
                                    ),
                                ],
                            ),
                            ft.TextButton("Continuar", on_click=lambda e, t=title: self._resume_extra_income_path(t)),
                        ],
                    ),
                )
            )

        return ft.Column(
            expand=True,
            controls=[
                self.header("Renda extra", "Do diagnóstico ao primeiro lucro, com acompanhamento"),
                ft.Container(
                    padding=16,
                    expand=True,
                    content=ft.Column(
                        scroll=ft.ScrollMode.ALWAYS,
                        spacing=12,
                        controls=[
                            ft.Container(
                                padding=16,
                                border_radius=20,
                                bgcolor="#17192B",
                                border=ft.Border.all(1,"#393266"),
                                content=ft.ResponsiveRow(
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                    controls=[
                                        ft.Container(col={"xs":4,"sm":2},alignment=ft.Alignment.CENTER,content=ft.Image(src=self.nex_asset("thinking","card"),width=120,height=120,fit=ft.BoxFit.CONTAIN)),
                                        ft.Container(
                                            col={"xs":8,"sm":10},
                                            content=ft.Column(
                                                spacing=7,
                                                controls=[
                                                    ft.Text("Nex, me ajuda a construir uma renda extra",size=18,weight=ft.FontWeight.BOLD),
                                                    ft.Text("Eu avalio 8 dimensões, comparo ideias e transformo a escolhida em uma Trilha Nex com missões, custos, checkpoints e acompanhamento opcional.",size=11,color=self.muted_color()),
                                                    ft.Row(
                                                        wrap=True,
                                                        controls=[
                                                            ft.Button("Explorar ideias",icon=ft.Icons.LIGHTBULB_OUTLINE,on_click=self.extra_income_dialog),
                                                            ft.OutlinedButton(
                                                                "Me ajude a escolher",
                                                                icon=ft.Icons.AUTO_AWESOME,
                                                                on_click=lambda e:self._start_nex_topic(
                                                                    "Quero uma renda extra. Me ajude a escolher considerando minha realidade.",
                                                                    source="extra_income",
                                                                    action="diagnose_extra_income",
                                                                ),
                                                            ),
                                                        ],
                                                    ),
                                                ],
                                            ),
                                        ),
                                    ],
                                ),
                            ),
                            ft.Text("Suas Trilhas Nex",size=17,weight=ft.FontWeight.BOLD),
                            *(journey if journey else [ft.Text("Você ainda não iniciou uma trilha. Explore uma ideia ou peça para o Nex ajudar a escolher.",size=10,color=self.muted_color())]),
                            ft.Container(
                                padding=15,
                                bgcolor=self.surface_color(),
                                border_radius=16,
                                border=ft.Border.all(1,self.border_color()),
                                content=ft.Column(
                                    spacing=5,
                                    controls=[
                                        ft.Text("Como saber se está valendo a pena",size=17,weight=ft.FontWeight.BOLD),
                                        ft.Text("Receita − materiais − taxas − deslocamento − outros custos = lucro real. Compare também lucro por hora e repetição da demanda antes de aumentar investimento.",size=11,color=self.muted_color()),
                                    ],
                                ),
                            ),
                            ft.Container(
                                padding=15,
                                bgcolor=self.surface_color(),
                                border_radius=16,
                                border=ft.Border.all(1,self.border_color()),
                                content=ft.Column(
                                    spacing=6,
                                    controls=[
                                        ft.Text("▶ Vídeos para se aprofundar",size=17,weight=ft.FontWeight.BOLD),
                                        ft.Text("Poucos materiais relevantes, no momento certo da trilha. Nada de repetir links em cada ideia.",size=10,color=self.muted_color()),
                                        ft.TextButton("Canal do Sebrae no YouTube",icon=ft.Icons.PLAY_CIRCLE_OUTLINE,on_click=lambda e:self.page.run_task(self.open_external_url,"https://www.youtube.com/@sebrae/videos")),
                                    ],
                                ),
                            ),
                        ],
                    ),
                ),
            ],
        )

    def _resume_extra_income_path(self, title):
        for t, m, g in EXTRA_INCOME_MANUALS:
            if t == title:
                self.extra_income_path_dialog(t, m, g)
                return

    def extra_income_dialog(self, e=None):
        controls=[]
        for title,meta,guide in EXTRA_INCOME_MANUALS:
            controls.append(
                ft.ExpansionTile(
                    title=ft.Text(title,weight=ft.FontWeight.BOLD),
                    subtitle=ft.Text(meta,size=10),
                    controls=[
                        ft.Container(
                            padding=12,
                            content=ft.Column(
                                spacing=9,
                                controls=[
                                    ft.Text(guide,size=11),
                                    ft.Row(
                                        wrap=True,
                                        controls=[
                                            ft.Button("Criar minha Trilha Nex",icon=ft.Icons.ROUTE,on_click=lambda e,t=title,m=meta,g=guide:self._create_journey(t,m,g)),
                                            ft.TextButton(
                                                "Conversar com o Nex",
                                                icon=ft.Icons.AUTO_AWESOME,
                                                on_click=lambda e,t=title:self._start_nex_topic(
                                                    f"Quero avaliar {t} como renda extra. Considere meu orçamento e me guie sem prometer ganho.",
                                                    source="extra_income",
                                                    entity_id=t,
                                                    action="evaluate_extra_income",
                                                ),
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        )
                    ],
                )
            )
        dialog_w, dialog_h = self.dialog_dimensions(620, 560)
        d=ft.AlertDialog(
            title=ft.Text("Ideias de renda extra"),
            content=ft.Column(
                width=dialog_w,
                height=dialog_h,
                scroll=ft.ScrollMode.ALWAYS,
                controls=[
                    ft.Text("Explore sem promessa de ganho. Depois transforme a opção escolhida numa Trilha Nex e teste pequeno antes de aumentar investimento.",size=11,color=self.muted_color()),
                    *controls,
                ],
            ),
            actions=[ft.TextButton("Fechar",on_click=lambda e:self.page.pop_dialog())],
        )
        self.page.show_dialog(d)

    def _create_journey(self, title, meta, guide):
        try:
            self.cloud.save_journey_progress(title,0,member_id=self.active_member_id,status="active")
            self._refresh_journeys()
            try: self.page.pop_dialog()
            except Exception: pass
            self.extra_income_path_dialog(title,meta,guide)
        except Exception:
            self.snack("Não consegui criar a trilha agora.",True)
