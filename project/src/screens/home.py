from ui.common import brl, datetime, ft, snapshot

class HomeScreen:
    def dashboard_data(self):
        return snapshot(self.cloud.all_income(), self.cloud.all_expenses_full(), self.month, self.members())


    def card(self, title, value, subtitle="", icon=ft.Icons.ACCOUNT_BALANCE_WALLET, color=ft.Colors.INDIGO):
        return ft.Container(
            col={"xs": 12, "sm": 6, "md": 4},
            padding=15, bgcolor=self.surface_color(), border_radius=16,
            border=ft.Border.all(1, self.border_color()),
            content=ft.Row(controls=[
                ft.Container(
                    width=46, height=46, border_radius=13,
                    bgcolor=ft.Colors.with_opacity(0.12, color),
                    alignment=ft.Alignment.CENTER,
                    content=ft.Icon(icon, color=color),
                ),
                ft.Column(expand=True, spacing=2, controls=[
                    ft.Text(title, size=11, color=self.muted_color()),
                    ft.Text(value, size=19, weight=ft.FontWeight.BOLD),
                    ft.Text(subtitle, size=10, color=self.subtle_color()),
                ]),
            ]),
        )


    def nex_mood(self, data):
        income=float(data.get("income") or 0); expense=float(data.get("expense") or 0)
        projected=float(data.get("projected_balance") or 0); pending=float(data.get("pending_month") or 0)
        ratio=(expense/income) if income else 0
        if income <= 0:
            return "curioso", "Ainda estou conhecendo este mês. Registre a renda e eu calibro meus alertas.", "#7C5CFF", "🤓"
        if projected < 0:
            return "preocupado", f"Temos {brl(pending)} pela frente e o saldo projetado fica em {brl(projected)}. Vamos reorganizar sem pânico.", "#FF7A59", "😟"
        if ratio > .90:
            return "atento", "O mês está bem comprometido. Eu ficaria de olho nas próximas saídas antes de assumir algo novo.", "#FFB020", "🧐"
        if ratio <= .60 and projected > 0:
            return "comemorando", "Boa! O mês está respirando. Dá para pensar em reserva e objetivos sem esquecer os próximos compromissos.", "#55E6A5", "🥳"
        return "tranquilo", "Seu mês está sob controle por enquanto. Eu continuo de olho nas próximas movimentações.", "#8B7CFF", "🙂"


    def nex_daily_panel(self, data):
        hour = datetime.now().hour
        greeting = "Bom dia" if hour < 12 else ("Boa tarde" if hour < 18 else "Boa noite")
        active=self.active_member(); who=(active or {}).get("display_name") or "família"
        mood, message, accent, face = self.nex_mood(data)
        self.nex_current_mood=mood
        mood_asset = {
            "curioso":self.nex_asset("idle","hero"),
            "preocupado":self.nex_asset("worry","hero"),
            "atento":self.nex_asset("thinking","hero"),
            "comemorando":self.nex_asset("celebrate","hero"),
            "tranquilo":self.nex_asset("idle","hero"),
        }.get(mood, self.nex_asset("idle","hero"))
        self.nex_idle_asset = mood_asset
        action_by_mood={
            "curioso":"curioso com as suas escolhas 👀", "preocupado":"fazendo contas com carinho 🧮",
            "atento":"de olho nos próximos gastos 🔎", "comemorando":"jogando moedas pro alto 🪙",
            "tranquilo":"de boa no galho 🌿",
        }
        bucket=self._layout_bucket(); phone=bucket=="phone"
        # O pack vinha em canvas 512x512 com muito espaço transparente. A pasta display/ já está recortada.
        nex_w = 96 if phone else 200
        nex_h = 96 if phone else 200
        nex_image = ft.Image(src=mood_asset, height=nex_h, width=nex_w, fit=ft.BoxFit.CONTAIN, gapless_playback=True)
        self.nex_float_image = nex_image
        nex = ft.Container(
            width=nex_w+18, height=nex_h+18, alignment=ft.Alignment.BOTTOM_RIGHT,
            offset=ft.Offset(0,0), scale=1.0, rotate=0,
            animate_offset=ft.Animation(850, ft.AnimationCurve.EASE_IN_OUT),
            animate_scale=ft.Animation(850, ft.AnimationCurve.EASE_IN_OUT),
            animate_rotation=ft.Animation(850, ft.AnimationCurve.EASE_IN_OUT),
            on_click=lambda e:self.page.run_task(self.nex_click_and_chat), tooltip=f"Nex está {mood} • toque para interagir",
            content=ft.Stack(controls=[
                ft.Container(right=2,bottom=2,content=nex_image),
                ft.Container(right=2,top=2,padding=ft.Padding.symmetric(horizontal=8,vertical=4),border_radius=12,bgcolor=accent,content=ft.Text(f"{face} {mood}",size=9,weight=ft.FontWeight.BOLD,color=ft.Colors.WHITE)),
            ])
        )
        coins=[]
        if mood == "comemorando":
            for left,top,icon in [(12,16,"🪙"),(56,2,"💰"),(105,18,"🪙")]:
                coin=ft.Container(left=left,top=top,opacity=.12,offset=ft.Offset(0,.08),animate_opacity=450,animate_offset=650,content=ft.Text(icon,size=22))
                nex.content.controls.append(coin); coins.append(coin)
        self.nex_coin_controls=coins; self.nex_float_control=nex
        text_col=12 if phone else 8
        nex_col=12 if phone else 4
        return ft.Container(
            padding=ft.Padding.only(left=16,right=10,top=8,bottom=0), border_radius=20,
            bgcolor="#15172A" if self.is_dark() else "#F0EEFF", border=ft.Border.all(1,"#39325E"),
            content=ft.ResponsiveRow(vertical_alignment=ft.CrossAxisAlignment.END, controls=[
                ft.Container(col=text_col, padding=ft.Padding.only(bottom=12), content=ft.Column(spacing=4, controls=[
                    ft.Text(f"{greeting}, {who}! 👋", size=20, weight=ft.FontWeight.BOLD),
                    ft.Text(message, size=11, color=self.muted_color()),
                    ft.Text(action_by_mood.get(mood,"por aqui com você 🦉"),size=9,color=accent,italic=True),
                    ft.Text("Disciplina hoje, liberdade amanhã.", size=10, italic=True, color="#9B8CFF"),
                    ft.TextButton("Conversar com o Nex", icon=ft.Icons.AUTO_AWESOME, on_click=lambda e:self._go_nex_chat()),
                ])),
                ft.Container(col=nex_col, alignment=ft.Alignment.BOTTOM_RIGHT if not phone else ft.Alignment.CENTER, content=nex),
            ])
        )


    def _mini_stat(self, title, value, icon, accent, subtitle=""):
        return ft.Container(col={"xs":12,"sm":4}, padding=12, border_radius=14, bgcolor=self.surface_color(),
            border=ft.Border.all(1,self.border_color()), content=ft.Column(spacing=3, controls=[
                ft.Icon(icon,size=19,color=accent), ft.Text(title,size=9,color=self.muted_color()),
                ft.Text(value,size=15,weight=ft.FontWeight.BOLD),
                ft.Text(subtitle,size=8,color=self.subtle_color(),max_lines=1,overflow=ft.TextOverflow.ELLIPSIS) if subtitle else ft.Container(height=0)
            ]))



    def _journey_reminder_due(self, journey, now=None):
        """Retorna True para lembretes opt-in vencidos no horário/dia local.

        É um lembrete *dentro do app*: não promete push do sistema operacional.
        Snooze fica nos ``metrics`` para sobreviver ao próximo render.
        """
        now = now or datetime.now()
        if not journey or not journey.get("reminder_enabled") or (journey.get("status") or "active") != "active":
            return False
        days = {int(x) for x in (journey.get("reminder_days") or []) if str(x).isdigit()}
        if days and now.isoweekday() not in days:
            return False
        raw = str((journey.get("metrics") or {}).get("reminder_time") or "")
        if not raw:
            anchor = str(journey.get("reminder_at") or "")
            try:
                raw = datetime.fromisoformat(anchor).strftime("%H:%M")
            except (TypeError, ValueError):
                return False
        try:
            hour, minute = (int(x) for x in raw.split(":", 1))
        except (ValueError, TypeError):
            return False
        due = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if now < due:
            return False
        snooze = str((journey.get("metrics") or {}).get("snooze_until") or "")
        if snooze:
            try:
                if now < datetime.fromisoformat(snooze):
                    return False
            except ValueError:
                pass
        return True

    def _snooze_journey_reminder(self, journey, minutes=60):
        try:
            from datetime import timedelta
            metrics = dict(journey.get("metrics") or {})
            metrics["snooze_until"] = (datetime.now() + timedelta(minutes=minutes)).isoformat()
            self.cloud.save_journey_progress(
                journey.get("title") or "Trilha",
                int(journey.get("progress") or 0),
                member_id=self.active_member_id,
                status=journey.get("status") or "active",
                reminder_enabled=bool(journey.get("reminder_enabled")),
                reminder_days=journey.get("reminder_days") or [],
                reminder_at=journey.get("reminder_at"),
                metrics=metrics,
            )
            self.extra_income_journeys = self.cloud.list_journeys(self.active_member_id)
            self.snack("Lembrete adiado por 1 hora.")
            self.render()
        except Exception:
            self.snack("Não consegui adiar o lembrete agora.", True)

    def dashboard(self):
        """Home app-first: responde como estamos, o que mudou e o que fazer."""
        d=self.dashboard_data()
        phone=self._layout_bucket()=="phone"
        future=float(d.get("pending_month") or 0)
        next_bill=(d.get("pending_rows") or [None])[0]
        family_balance=float(d.get("balance") or 0)
        projected=float(d.get("projected_balance") or 0)

        members=self.members()
        people=[]
        for m in members:
            mid=str(m["id"])
            available=float(d.get("member_balance",{}).get(mid,0))
            pending=float(d.get("member_pending",{}).get(mid,0))
            people.append(ft.Container(
                col={"xs":6,"md":3},padding=11,border_radius=15,bgcolor=self.surface_alt_color(),
                content=ft.Column(spacing=2,controls=[
                    ft.Text(m.get("display_name") or "Pessoa",size=10,color=self.muted_color()),
                    ft.Text(brl(available),size=17,weight=ft.FontWeight.BOLD,color="#55E6A5" if available>=0 else ft.Colors.RED),
                    ft.Text((f"{brl(pending)} futuro" if pending else "sem conta futura atribuída"),size=8,color=self.subtle_color(),max_lines=1,overflow=ft.TextOverflow.ELLIPSIS),
                ])
            ))

        cash_card=ft.Container(
            padding=18,border_radius=22,bgcolor="#111827" if self.is_dark() else ft.Colors.WHITE,
            border=ft.Border.all(1,self.border_color()),
            content=ft.Column(spacing=10,controls=[
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN,controls=[
                    ft.Column(expand=True,spacing=2,controls=[
                        ft.Text("Disponível para a família hoje",size=11,color=self.muted_color()),
                        ft.Text(brl(family_balance),size=32 if not phone else 28,weight=ft.FontWeight.BOLD,color="#55E6A5" if family_balance>=0 else ft.Colors.RED),
                        ft.Text(f"Depois dos compromissos registrados: {brl(projected)}",size=9,color=self.muted_color()),
                    ]),
                    ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,color="#8B7CFF",size=34),
                ]),
                ft.Container(padding=10,border_radius=13,bgcolor=self.surface_alt_color(),content=ft.Row(controls=[
                    ft.Icon(ft.Icons.EVENT_UPCOMING,color=ft.Colors.ORANGE,size=18),
                    ft.Column(expand=True,spacing=1,controls=[
                        ft.Text("Próximo compromisso",size=9,color=self.muted_color()),
                        ft.Text((f"{next_bill.get('description','Conta')} • {brl(next_bill.get('amount',0))} • {next_bill.get('expense_date','')}" if next_bill else "Nenhuma conta pendente registrada."),size=11,weight=ft.FontWeight.BOLD,max_lines=2,overflow=ft.TextOverflow.ELLIPSIS),
                    ]),
                    ft.TextButton("Ver",on_click=lambda e:self._go_movement_tab(1)),
                ])),
                ft.Text(f"Neste mês entraram {brl(d.get('income',0))} e saíram {brl(d.get('expense',0))} já efetivados.",size=10,color=self.muted_color()),
            ])
        )

        attention=[]
        if next_bill:
            attention.append(("📅","Conta chegando",f"{next_bill.get('description','Conta')} vence em {next_bill.get('expense_date','')} • {brl(next_bill.get('amount',0))}"))
        top=(d.get("categories") or [])[:1]
        if top:
            attention.append(("👀","Maior gasto do mês",f"{top[0][0]} está em {brl(top[0][1])}. Toque em Análises para entender o impacto."))
        if projected < 0:
            attention.insert(0,("⚠️","Saldo projetado negativo",f"Depois das contas registradas, o caixa projetado fica em {brl(projected)}."))
        for issue in d.get("issues",[])[:1]:
            attention.append(("🧩","Registro precisa de atenção",issue))
        if not attention:
            attention.append(("✅","Nada urgente agora","Continue registrando as movimentações; o Nex avisa quando houver algo relevante."))

        attention_cards=[ft.Container(
            col={"xs":12,"md":4},padding=12,border_radius=15,bgcolor=self.surface_color(),border=ft.Border.all(1,self.border_color()),
            content=ft.Row(vertical_alignment=ft.CrossAxisAlignment.START,controls=[
                ft.Text(icon,size=23),
                ft.Column(expand=True,spacing=2,controls=[ft.Text(title,weight=ft.FontWeight.BOLD,size=12),ft.Text(text,size=9,color=self.muted_color(),max_lines=3,overflow=ft.TextOverflow.ELLIPSIS)])
            ])
        ) for icon,title,text in attention[:3]]

        journey_card=ft.Container(height=0)
        active_journeys=[r for r in getattr(self,"extra_income_journeys",[]) if (r.get("status") or "active")=="active"]
        if active_journeys:
            due_journey=next((r for r in active_journeys if self._journey_reminder_due(r)),None)
            j=due_journey or active_journeys[0]
            progress=int(j.get("progress") or 0)
            due=bool(due_journey)
            journey_card=ft.Container(
                padding=14,border_radius=17,bgcolor="#17192B",border=ft.Border.all(1,"#6B5CFF" if due else "#393266"),
                content=ft.ResponsiveRow(vertical_alignment=ft.CrossAxisAlignment.CENTER,controls=[
                    ft.Container(col={"xs":2,"sm":1},alignment=ft.Alignment.CENTER,content=ft.Icon(ft.Icons.NOTIFICATIONS_ACTIVE if due else ft.Icons.ROUTE,color="#A99CFF" if due else "#8B7CFF",size=27)),
                    ft.Container(col={"xs":10,"sm":8},content=ft.Column(spacing=3,controls=[
                        ft.Text("Missão da Trilha Nex para agora" if due else "Continue sua Trilha Nex",weight=ft.FontWeight.BOLD),
                        ft.Text(j.get("title") or "Renda extra",size=10,color=self.muted_color()),
                        ft.ProgressBar(value=min(progress/10,1),color="#7C5CFF"),
                        ft.Text(("🦉 Seu lembrete chegou • " if due else "")+f"Etapa {min(progress+1,10)} de 10 • {int(progress/10*100)}%",size=8,color=self.subtle_color()),
                    ])),
                    ft.Container(col={"xs":12,"sm":3},content=ft.Row(wrap=True,controls=[
                        ft.TextButton("Continuar",on_click=lambda e,t=j.get("title"):self._resume_extra_income_path(t)),
                        ft.TextButton("Adiar 1h",visible=due,on_click=lambda e,row=j:self._snooze_journey_reminder(row)),
                    ])),
                ])
            )

        return ft.Column(expand=True,scroll=ft.ScrollMode.AUTO,controls=[
            self.header("NexGrana","Sua grana. Seu próximo nível."),
            ft.Container(padding=12 if phone else 14,content=ft.Column(spacing=12,controls=[
                self.nex_daily_panel(d),
                cash_card,
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN,controls=[
                    ft.Text("Como está dividido",size=15,weight=ft.FontWeight.BOLD),
                    ft.Text("saldo individual após gastos e rateios",size=8,color=self.muted_color()),
                ]),
                ft.ResponsiveRow(spacing=8,run_spacing=8,controls=people),
                ft.Text("O que merece atenção",size=15,weight=ft.FontWeight.BOLD),
                ft.ResponsiveRow(spacing=8,run_spacing=8,controls=attention_cards),
                journey_card,
                ft.Row(wrap=True,controls=[
                    ft.Button("+ Renda",icon=ft.Icons.ADD,on_click=self.income_dialog),
                    ft.Button("+ Despesa",icon=ft.Icons.ADD,on_click=self.expense_dialog),
                    ft.OutlinedButton("Entender meu mês",icon=ft.Icons.INSIGHTS,on_click=lambda e:(setattr(self,"assistant_tab",0),self._go_screen(3))),
                    ft.OutlinedButton("Falar com o Nex",icon=ft.Icons.AUTO_AWESOME,on_click=lambda e:self._go_nex_chat()),
                ])
            ]))
        ])

