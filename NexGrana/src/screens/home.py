from ui.common import brl, dashboard_labels, datetime, ft, member_snapshot, month_label, snapshot
from datetime import date
import calendar
from services.monthly_ledger import (
    month_has_activity,
    month_is_closed,
    opening_balance_for_month,
    previous_month,
)

class HomeScreen:
    def _load_month_closures(self):
        try:
            self._month_closure_error = None
            return list(self.cloud.list_month_closures())
        except AttributeError:
            self._month_closure_error = None
            return []
        except Exception as exc:
            self._month_closure_error = type(exc).__name__
            return []

    def month_close_needed(self, month):
        incomes = self.cloud.all_income()
        expenses = self.cloud.all_expenses_full()
        closures = self._load_month_closures()
        if self._month_closure_error:
            return month_has_activity(incomes, expenses, month)
        scopes = [None]
        if self.is_family_space():
            scopes.extend(str(row.get("id")) for row in self.members() if row.get("id"))
        else:
            active = self.active_member()
            scopes = [str(active.get("id"))] if active and active.get("id") else []
        if not scopes:
            return False
        return any(
            (month_has_activity(incomes, expenses, month, scope)
             or month_is_closed(closures, previous_month(month), scope))
            and not month_is_closed(closures, month, scope)
            for scope in scopes
        )

    def month_closure_card(self, month):
        title = month_label(month)
        blocked = bool(self._month_closure_error)
        message = (
            "Não consegui consultar os fechamentos. Confira a conexão, as permissões e a migração 0.25. O saldo anterior não foi confirmado."
            if blocked else
            f"Confira as movimentações de {title} e confirme o fechamento para levar o saldo aos próximos meses."
        )
        return ft.Container(
            padding=14,
            border_radius=16,
            bgcolor=self.surface_color(),
            border=ft.Border.all(1, ft.Colors.ORANGE_400),
            content=ft.ResponsiveRow(vertical_alignment=ft.CrossAxisAlignment.CENTER, controls=[
                ft.Container(col={"xs": 2, "sm": 1}, alignment=ft.Alignment.CENTER,
                             content=ft.Icon(ft.Icons.EVENT, color=ft.Colors.ORANGE_400, size=26)),
                ft.Container(col={"xs": 10, "sm": 8}, content=ft.Column(spacing=3, controls=[
                    ft.Text(f"Fechamento de {title} pendente", weight=ft.FontWeight.BOLD, size=12),
                    ft.Text(message, size=10, color=self.muted_color()),
                ])),
                ft.Container(col={"xs": 12, "sm": 3}, content=ft.Button(
                    "Ver instruções" if blocked else "Revisar mês",
                    icon=ft.Icons.CHECK,
                    on_click=lambda e, selected=month: self.month_closure_help() if blocked else self.close_month_dialog(selected),
                )),
            ]),
        )

    def month_closure_help(self):
        self.page.show_dialog(ft.AlertDialog(title=ft.Text("Preparar o fechamento do mês"),content=ft.Column(tight=True,controls=[
            ft.Text("1. Reconecte e sincronize a conta. Se já houver uma cópia local, confira as pendências de sincronização."),
            ft.Text("2. No ambiente de homologação, o administrador deve confirmar a tabela monthly_closures e revisar MIGRATION_0_25.sql, com backup e teste de permissões."),
            ft.Text("3. Volte à Home e tente revisar o mês. Até confirmar o fechamento, o saldo do mês anterior não é transportado."),
            ft.Text("Esta tela não aplica migrations nem modifica seu saldo.",size=11,color=self.muted_color()),
        ]),actions=[ft.TextButton("Entendi",on_click=lambda e:self.page.pop_dialog())]))

    def close_month_dialog(self, month, continue_to=None):
        incomes = self.cloud.all_income()
        expenses = self.cloud.all_expenses_full()
        members = self.members()
        closures = self._load_month_closures()
        scopes = [None]
        if self.is_family_space():
            scopes.extend(str(row.get("id")) for row in members if row.get("id"))
        else:
            active = self.active_member()
            scopes = [str(active.get("id"))] if active and active.get("id") else []
        if not scopes:
            self.snack("Não há perfil ativo para fechar este mês. Selecione um perfil e tente novamente.", True)
            return

        previews = []
        for scope in scopes:
            opening = opening_balance_for_month(incomes, expenses, closures, month, members, scope)
            result = (
                snapshot(incomes, expenses, month, members=members, opening_balance=opening)
                if scope is None else
                member_snapshot(incomes, expenses, month, scope, members=members, opening_balance=opening)
            )
            label = "Saldo consolidado da família" if scope is None else next(
                (row.get("display_name") for row in members if str(row.get("id")) == scope), "Perfil"
            )
            previews.append((scope, opening, result, label))

        period_month, period_year = map(int, month.split("/"))
        period_end = date(period_year, period_month, calendar.monthrange(period_year, period_month)[1])
        period_finished = date.today() > period_end
        lines = [ft.Text("Confirme que as rendas e despesas deste mês foram revisadas.", size=12)]
        lines.append(ft.Text("Lançamentos atrasados podem ser incluídos depois: se tiverem data deste mês, o saldo levado será recalculado.", size=10, color=self.muted_color()))
        if not period_finished:
            lines.append(ft.Text("Este mês ainda está em andamento. Você pode abrir o próximo, mas o fechamento só fica disponível depois do último dia.", color=ft.Colors.ORANGE_400, size=10))
        lines.extend(ft.Text(
            f"{label}: transportado {brl(result.get('opening_balance', 0))} • renda {brl(result.get('income', 0))} • "
            f"despesas {brl(result.get('expense', 0))} • futuro {brl(result.get('pending_month', 0))} • "
            f"saldo {brl(result.get('balance', 0))}",
            weight=ft.FontWeight.BOLD,
            size=11,
        ) for _, _, result, label in previews)
        if self._month_closure_error:
            lines.append(ft.Text("Não consegui ler os fechamentos salvos. Confira se a migração 0.25 foi aplicada e tente novamente.", color=ft.Colors.RED_400, size=10))

        dialog = ft.AlertDialog(
            title=ft.Text(f"Fechar {month_label(month)}?"),
            content=ft.Column(tight=True, scroll=ft.ScrollMode.AUTO, controls=lines),
        )

        def confirm(_):
            try:
                pending=False
                values=[(scope,opening,result.get('balance',0)) for scope,opening,result,_label in previews]
                results=self.cloud.save_month_closures(month,values) if hasattr(self.cloud,'save_month_closures') else [self.cloud.save_month_closure(month,*value) for value in values]
                for saved in results:
                    pending=pending or (isinstance(saved,dict) and saved.get("_sync_state")!="synced")
                self.page.pop_dialog()
                if continue_to:
                    self.month = continue_to
                self.last_cloud_snapshot = None
                self.render()
                self.snack("Fechamento confirmado neste aparelho; sincronização pendente. Confira a fila ao reconectar." if pending else "Fechamento confirmado e sincronizado. Lançamentos retroativos recalculam a continuidade.")
            except Exception as exc:
                self.snack("Não foi possível confirmar todos os fechamentos. Confira as pendências, a conexão e a migração 0.25 antes de repetir.", True)

        def review_month(_):
            self.page.pop_dialog()
            self.month = month
            self.last_cloud_snapshot = None
            self.render()

        actions = [
            ft.TextButton("Fechar sem confirmar", on_click=lambda e: self.page.pop_dialog()),
            ft.TextButton("Ver movimentações", on_click=review_month),
        ]
        if continue_to:
            def continue_without_close(_):
                self.page.pop_dialog()
                self.month = continue_to
                self.last_cloud_snapshot = None
                self.render()
                self.snack("Mês aberto sem fechamento; o saldo anterior ainda não foi transportado.", True)
            actions.append(ft.TextButton("Continuar sem levar saldo", on_click=continue_without_close))
        if not self._month_closure_error:
            actions.append(ft.Button(
                "Fechar e continuar" if continue_to else "Confirmar fechamento",
                icon=ft.Icons.CHECK,
                disabled=not period_finished,
                on_click=confirm,
            ))
        dialog.actions = actions
        self.page.show_dialog(dialog)

    def dashboard_data(self, incomes=None, expenses=None):
        """Resumo determinístico do perfil ativo; nunca mistura integrantes."""
        members = self.members()
        active = self.active_member()
        income_rows = self.cloud.all_income() if incomes is None else incomes
        expense_rows = self.cloud.all_expenses_full() if expenses is None else expenses
        closures = self._load_month_closures()
        scope = str(active.get("id")) if active and active.get("id") else ""
        opening = opening_balance_for_month(income_rows, expense_rows, closures, self.month, members, scope) if scope else 0
        result = member_snapshot(
            income_rows,
            expense_rows,
            self.month,
            scope,
            members,
            opening_balance=opening,
        )
        if self._month_closure_error:
            result["issues"].append("Continuidade mensal indisponível até aplicar a migração 0.25 no Supabase.")
        elif (month_has_activity(income_rows, expense_rows, previous_month(self.month), scope)
              or month_is_closed(closures, previous_month(previous_month(self.month)), scope)) \
                and not month_is_closed(closures, previous_month(self.month), scope):
            result["issues"].append("O mês anterior tem movimentações e ainda não foi confirmado para transportar o saldo.")
        return result


    def family_dashboard_data(self, incomes=None, expenses=None):
        """Consolidado familiar explícito, usado apenas em blocos identificados."""
        income_rows = self.cloud.all_income() if incomes is None else incomes
        expense_rows = self.cloud.all_expenses_full() if expenses is None else expenses
        closures = self._load_month_closures()
        opening = opening_balance_for_month(income_rows, expense_rows, closures, self.month, self.members(), None)
        result = snapshot(
            income_rows,
            expense_rows,
            self.month,
            self.members(),
            opening_balance=opening,
        )
        if self._month_closure_error:
            result["issues"].append("Continuidade familiar indisponível até aplicar a migração 0.25 no Supabase.")
        return result


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
        active=self.active_member(); who=(active or {}).get("display_name") or self.space_copy("você", "família")
        mood, message, accent, face = self.nex_mood(data)
        self.nex_current_mood=mood
        bucket=self._layout_bucket(); phone=bucket=="phone"
        mood_asset = {
            "curioso":self.nex_asset("idle","hero",context="home"),
            "preocupado":self.nex_asset("worry","hero",context="home"),
            "atento":self.nex_asset("thinking","hero",context="home"),
            "comemorando":self.nex_asset("celebrate","hero",context="home"),
            "tranquilo":self.nex_asset("idle","hero",context="home"),
        }.get(mood, self.nex_asset("idle","hero",context="home"))
        # The welcoming pose is a Home-only variant. Other Nex contexts keep the
        # canonical pack until each expression has been checked individually.
        mood_asset = {
            "curioso":"nex/nex_welcome_v2.png",
            "tranquilo":"nex/nex_welcome_v2.png",
            "atento":"nex/nex_thinking_v2.png",
            "preocupado":"nex/nex_thinking_v2.png",
            "comemorando":"nex/nex_celebrate_v2.png",
        }.get(mood,mood_asset)
        from services.nex_skins import skin_asset
        mood_asset=skin_asset(self.preferences, role="compact" if phone else "hero", context="home") or mood_asset
        self.nex_idle_asset = mood_asset
        action_by_mood={
            "curioso":"curioso com as suas escolhas 👀", "preocupado":"fazendo contas com carinho 🧮",
            "atento":"de olho nos próximos gastos 🔎", "comemorando":"jogando moedas pro alto 🪙",
            "tranquilo":"de boa no galho 🌿",
        }
        # O pack vinha em canvas 512x512 com muito espaço transparente. A pasta display/ já está recortada.
        nex_w = 94 if phone else 188
        nex_h = 94 if phone else 188
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
        if mood == "comemorando" and self.nex_state.settings.effects and not self.nex_state.settings.reduced_motion:
            for left,top,icon in [(12,16,"🪙"),(56,2,"💰"),(105,18,"🪙")]:
                coin=ft.Container(left=left,top=top,opacity=.12,offset=ft.Offset(0,.08),animate_opacity=450,animate_offset=650,content=ft.Text(icon,size=22))
                nex.content.controls.append(coin); coins.append(coin)
        self.nex_coin_controls=coins; self.nex_float_control=nex
        text_col=8
        nex_col=4
        theme_accent=self.visual_style()["accent"]
        return ft.Container(
            padding=ft.Padding.only(left=20,right=10,top=18,bottom=12), border_radius=22,
            gradient=ft.LinearGradient(
                begin=ft.Alignment.TOP_LEFT,end=ft.Alignment.BOTTOM_RIGHT,
                colors=[self.surface_color(),self.surface_alt_color(),"#25205E" if self.is_dark() and self.preferences.get("visual_style")!="tech" else ("#123D50" if self.is_dark() else "#E7E4FF")],
            ),
            border=ft.Border.all(1,theme_accent),
            shadow=ft.BoxShadow(blur_radius=22,spread_radius=0,color=ft.Colors.with_opacity(.18,theme_accent),offset=ft.Offset(0,6)),
            content=ft.ResponsiveRow(vertical_alignment=ft.CrossAxisAlignment.END, controls=[
                ft.Container(col=text_col, padding=ft.Padding.only(bottom=12), content=ft.Column(spacing=4, controls=[
                    ft.Text(f"{greeting}, {who}! 👋", size=17 if phone else 27, weight=ft.FontWeight.BOLD),
                    ft.Text(message, size=10 if phone else 13, color=self.muted_color(),max_lines=3,overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text("Disciplina hoje, liberdade amanhã.", size=10 if phone else 13, italic=True, color="#BCA7FF" if self.is_dark() else "#5845AD"),
                    ft.Button("Conversar com o Nex", icon=ft.Icons.AUTO_AWESOME, on_click=lambda e:self._go_nex_chat()),
                ])),
                ft.Container(col=nex_col, alignment=ft.Alignment.BOTTOM_RIGHT, content=nex),
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
        incomes=self.cloud.all_income()
        expenses=self.cloud.all_expenses_full()
        closures=self._load_month_closures()
        d=self.dashboard_data(incomes,expenses)
        family_data=self.family_dashboard_data(incomes,expenses)
        phone=self._layout_bucket()=="phone"
        future=float(d.get("pending_month") or 0)
        next_bill=(d.get("pending_rows") or [None])[0]
        active_balance=float(d.get("balance") or 0)
        projected=float(d.get("projected_balance") or 0)
        active_name=(self.active_member() or {}).get("display_name") or "Perfil"
        labels=dashboard_labels(getattr(self.cloud,"household",None))

        members=self.members()
        people=[]
        for m in members:
            mid=str(m["id"])
            member_opening = opening_balance_for_month(incomes, expenses, closures, self.month, members, mid)
            member_data = member_snapshot(incomes, expenses, self.month, mid, members=members, opening_balance=member_opening)
            available=float(member_data.get("balance",0))
            pending=float(family_data.get("member_pending",{}).get(mid,0))
            people.append(ft.Container(
                col={"xs":6,"md":3},padding=11,border_radius=15,bgcolor=self.surface_alt_color(),
                content=ft.Column(spacing=2,controls=[
                    ft.Text(m.get("display_name") or labels["empty_person"],size=10,color=self.muted_color()),
                    ft.Text(brl(available),size=17,weight=ft.FontWeight.BOLD,color="#55E6A5" if available>=0 else ft.Colors.RED),
                    ft.Text((f"{brl(pending)} futuro" if pending else "sem conta futura atribuída"),size=8,color=self.subtle_color(),max_lines=1,overflow=ft.TextOverflow.ELLIPSIS),
                ])
            ))

        cash_card=ft.Container(
            padding=18,border_radius=22,bgcolor=self.surface_color(),
            border=ft.Border.all(1,self.border_color()),
            content=ft.Column(spacing=10,controls=[
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN,controls=[
                    ft.Column(expand=True,spacing=2,controls=[
                        ft.Text(f"Saldo atual de {active_name} neste mês",size=11,color=self.muted_color()),
                        ft.Text(brl(active_balance),size=32 if not phone else 28,weight=ft.FontWeight.BOLD,color="#36DFAE" if active_balance>=0 else ft.Colors.RED),
                        ft.Text(f"Saldo transportado: {brl(d.get('opening_balance',0))}",size=9,color=self.muted_color()),
                        ft.Text(f"Projetado após despesas futuras deste mês: {brl(projected)}",size=9,color=self.muted_color()),
                    ]),
                    ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,color="#8B7CFF",size=34),
                ]),
                ft.Container(padding=10,border_radius=13,bgcolor=self.surface_alt_color(),content=ft.Row(controls=[
                    ft.Icon(ft.Icons.EVENT,color=ft.Colors.ORANGE,size=18),
                    ft.Column(expand=True,spacing=1,controls=[
                        ft.Text("Próxima despesa futura deste mês",size=9,color=self.muted_color()),
                        ft.Text((f"{next_bill.get('description','Conta')} • {brl(next_bill.get('amount',0))} • {next_bill.get('expense_date','')}" if next_bill else "Nenhuma conta pendente registrada."),size=11,weight=ft.FontWeight.BOLD,max_lines=2,overflow=ft.TextOverflow.ELLIPSIS),
                    ]),
                    ft.TextButton("Ver",on_click=lambda e:self._go_movement_tab(1)),
                ])),
                ft.ResponsiveRow(spacing=8,run_spacing=8,controls=[
                    ft.Container(col={"xs":6,"md":4},content=self._mini_stat("Entradas",brl(d.get('income',0)),ft.Icons.ARROW_UPWARD,"#36DFAE")),
                    ft.Container(col={"xs":6,"md":4},content=self._mini_stat("Saídas",brl(d.get('expense',0)),ft.Icons.ARROW_DOWNWARD,"#FF668B")),
                    ft.Container(col={"xs":12,"md":4},content=self._mini_stat("Projeção do mês",brl(projected),ft.Icons.TRENDING_UP,"#23D5F3")),
                ]),
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
                padding=14,border_radius=17,bgcolor=self.surface_alt_color(),border=ft.Border.all(1,"#6B5CFF" if due else self.border_color()),
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

        family_balance=ft.Container(
            padding=16,border_radius=18,bgcolor=self.surface_color(),
            border=ft.Border.all(1,self.border_color()),
            content=ft.ResponsiveRow(spacing=8,run_spacing=8,controls=[
                ft.Container(col={"xs":12,"sm":6},content=ft.Column(spacing=3,controls=[
                    ft.Text("Saldo da família neste mês",size=12,color=self.muted_color()),
                    ft.Text(brl(family_data.get("balance",0)),size=25,weight=ft.FontWeight.BOLD),
                    ft.Text(f"Saldo transportado: {brl(family_data.get('opening_balance',0))}",size=9,color=self.muted_color()),
                    ft.Text("Consolidado dos integrantes e rateios, sem misturar os saldos individuais.",size=10,color=self.subtle_color()),
                ])),
                ft.Container(col={"xs":12,"sm":6},content=ft.Column(spacing=4,controls=[
                    ft.Text(f"Renda conjunta: {brl(family_data.get('income',0))}",size=11),
                    ft.Text(f"Despesas já efetivadas: {brl(family_data.get('expense',0))}",size=11),
                    ft.Text(f"Compromissos futuros: {brl(family_data.get('pending_month',0))}",size=11),
                ])),
            ]),
        ) if self.is_family_space() else ft.Container(height=0)

        prior_month = previous_month(self.month)
        closure_pending = self.month_close_needed(prior_month)
        closure_card = self.month_closure_card(prior_month) if closure_pending else ft.Container(height=0)

        return ft.Column(expand=True,scroll=ft.ScrollMode.AUTO,controls=[
            self.header("NexGrana","Sua grana. Seu próximo nível."),
            ft.Container(padding=12 if phone else 14,content=ft.Column(spacing=12,controls=[
                self.nex_daily_panel(d),
                closure_card,
                cash_card,
                family_balance,
                ft.Text("Saldos por integrante",size=15,weight=ft.FontWeight.BOLD) if self.is_family_space() else ft.Container(height=0),
                ft.ResponsiveRow(spacing=8,run_spacing=8,controls=people) if self.is_family_space() else ft.Container(height=0),
                ft.Row(wrap=True,controls=[
                    ft.Button("+ Renda",icon=ft.Icons.ADD,on_click=self.income_dialog),
                    ft.Button("+ Despesa",icon=ft.Icons.ADD,on_click=self.expense_dialog),
                    ft.OutlinedButton("Saúde financeira",icon=ft.Icons.INSIGHTS,on_click=lambda e:self.analysis_dialog()),
                    ft.OutlinedButton("Falar com o Nex",icon=ft.Icons.AUTO_AWESOME,on_click=lambda e:self._go_nex_chat()),
                    ft.OutlinedButton("Achados",icon=ft.Icons.LOCAL_OFFER_OUTLINED,on_click=lambda e:self._go_market_tab("Achados")),
                ]),
                ft.Text("O que merece atenção",size=15,weight=ft.FontWeight.BOLD),
                ft.ResponsiveRow(spacing=8,run_spacing=8,controls=attention_cards),
                journey_card,
            ]))
        ])
