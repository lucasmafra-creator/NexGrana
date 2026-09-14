from screens.home import HomeScreen
from screens.movements import MovementsScreen
from screens.acquisitions import AcquisitionsScreen
from screens.planning import PlanningScreen
from screens.market import MarketScreen
from screens.nex import NexScreen
from screens.analysis import AnalysisScreen
from screens.extra_income import ExtraIncomeScreen
from screens.settings import SettingsScreen
from screens.auth import AuthScreen
from ui.theme import ThemeScreen
from services.performance import PerformanceMonitor
from services.analytics import AnalyticsAdapter
from ui.common import Cloud, NexEngine, NexStateMachine, add_months, asyncio, brl, bucket, datetime, ft, logger, month_key, month_label, storage_dir

class NexGranaCloud(HomeScreen,MovementsScreen,AcquisitionsScreen,PlanningScreen,MarketScreen,NexScreen,AnalysisScreen,ExtraIncomeScreen,SettingsScreen,AuthScreen,ThemeScreen):
    def __init__(self, page: ft.Page, vault=None):
        self.page = page
        self.cloud = Cloud(vault=vault)
        self.month = month_key()
        self.screen = 0
        self.sync_task_started = False
        self.last_sync = "—"
        self.last_cloud_snapshot = None
        self.chat_messages = []
        self.nex_busy = False
        self.nex_draft = ""
        self.chat_pending = None
        self.chat_aliases = {}
        self.chat_context = None
        self.movement_tab = 0
        self.assistant_tab = 0
        self.expense_person_filter = "Todos"
        self.expense_order = "recent"
        self.expense_group = False
        self.preferences_path = storage_dir() / "preferences.json"
        self.preferences = self.load_preferences()
        self.active_member_id = self.preferences.get("active_member_id")
        self.nex_float_control = None
        self.nex_float_image = None
        self.nex_coin_controls = []
        self.last_layout_bucket = None
        self.chat_memory = {"last_topic": None, "last_user_mood": None, "last_intent": None}
        self.extra_income_path = {}
        self.extra_income_journeys = []
        self.nex_engine = NexEngine(self)
        self.nex_state = NexStateMachine()
        self.receipt_photos = []
        self.nex_last_hint = None
        self.page.on_resize = self.on_page_resized
        self.nex_action_label = None
        self.nex_motion_phase = 0
        self.nex_animation_started = False
        self.page.title = "NexGrana 0.19.0"
        self.perf = PerformanceMonitor()
        self.analytics = AnalyticsAdapter(enabled=False)
        self.root_host = None
        self.root_safe_area = None
        self._last_render_signature = None
        self.page.theme_mode = ft.ThemeMode.DARK if self.preferences.get("dark_mode", True) else ft.ThemeMode.LIGHT
        self.apply_theme()
        self.page.bgcolor = self.page_color()
        self.page.padding = 0
        self.page.adaptive = True
        self.render_entry()


    def _layout_bucket(self):
        return bucket(self.page.width)


    def dialog_dimensions(self, max_width=620, max_height=620):
        """Tamanho seguro para dialogs em celular, tablet e desktop.

        Reserva espaço para barras do sistema/teclado e evita conteúdo maior que
        o viewport. O scroll continua responsabilidade do conteúdo do dialog.
        """
        width=float(self.page.width or max_width)
        height=float(self.page.height or max_height)
        safe_w=max(260, min(float(max_width), width - (28 if width < 700 else 64)))
        safe_h=max(300, min(float(max_height), height - (150 if height < 900 else 180)))
        return safe_w, safe_h


    def on_page_resized(self, e=None):
        """Reconstrói a composição somente quando muda de faixa de layout.
        Evita mês/perfil saírem da tela ao redimensionar notebook, tablet e celular.
        """
        bucket = self._layout_bucket()
        if bucket != self.last_layout_bucket:
            self.last_layout_bucket = bucket
            try:
                self.render()
            except Exception:
                pass


    def load_preferences(self):
        theme = {}
        try:
            import json
            if self.preferences_path.exists():
                legacy = json.loads(self.preferences_path.read_text(encoding="utf-8"))
                theme = {"dark_mode": bool(legacy.get("dark_mode", True))}
                # Only the non-personal theme is retained outside the encrypted vault.
                self.preferences_path.write_text(json.dumps(theme), encoding="utf-8")
            if self.cloud.user and self.cloud.household and self.cloud.vault:
                return {**theme, **self.cloud.vault.read("preferences:" + self.cloud._scope(), {})}
        except (OSError, ValueError):
            logger.warning("preferences_read_failed")
        return theme


    def save_preferences(self):
        import json
        self.preferences_path.write_text(json.dumps({"dark_mode": self.preferences.get("dark_mode", True)}), encoding="utf-8")
        if self.cloud.user and self.cloud.household and self.cloud.vault:
            self.cloud.vault.write("preferences:" + self.cloud._scope(), self.preferences)


    def change_month(self, offset):
        self.month = add_months(self.month, offset)
        self.last_cloud_snapshot = None
        self.render()


    def snack(self, text, error=False):
        self.page.show_dialog(
            ft.SnackBar(
                ft.Text(text),
                bgcolor=ft.Colors.RED_700 if error else ft.Colors.GREEN_700,
            )
        )


    def start_app(self):
        self.preferences = self.load_preferences()
        self.active_member_id = self.preferences.get("active_member_id")
        self.page.clean()
        self.root_host = None
        self.root_safe_area = None
        self.screen = 0
        selected=self.active_member()
        if selected:
            self.active_member_id=str(selected.get("id"))
            self.preferences["active_member_id"]=self.active_member_id
            self.save_preferences()
        self.extra_income_journeys = self.cloud.list_journeys(self.active_member_id)
        self.extra_income_path = self.cloud.load_journey_progress(self.active_member_id)
        self.page.navigation_bar = ft.NavigationBar(
            selected_index=0,
            on_change=self.on_nav,
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.HOME_OUTLINED, selected_icon=ft.Icons.HOME, label="Início"),
                ft.NavigationBarDestination(icon=ft.Icons.SWAP_HORIZ, selected_icon=ft.Icons.SWAP_HORIZ, label="Transações"),
                ft.NavigationBarDestination(icon=ft.Icons.TRACK_CHANGES, label="Planejamento"),
                ft.NavigationBarDestination(icon=ft.Icons.AUTO_AWESOME_OUTLINED, selected_icon=ft.Icons.AUTO_AWESOME, label="Nex"),
                ft.NavigationBarDestination(icon=ft.Icons.SETTINGS_OUTLINED, selected_icon=ft.Icons.SETTINGS, label="Mais"),
            ],
        )
        self.render()
        try:
            self.last_cloud_snapshot = self.cloud_snapshot()
        except Exception:
            self.last_cloud_snapshot = None
        if not self.sync_task_started:
            self.sync_task_started = True
            self.page.run_task(self.auto_sync_loop)
        if not self.nex_animation_started:
            self.nex_animation_started = True
            self.page.run_task(self.nex_animation_loop)


    async def nex_animation_loop(self):
        """Mantém o Nex visível e vivo com micro movimentos + ações ocasionais."""
        phase = 0
        while True:
            await asyncio.sleep(1.0)
            try:
                c = self.nex_float_control
                if c is None:
                    continue
                phase = (phase + 1) % 12
                p = phase % 6
                motion=self.nex_state.motion(phase)
                drift=[-0.010,0.008,0.014,0.0,-0.008,0.0][p]
                c.offset=ft.Offset(drift,float(motion.get("dy",0)))
                c.scale=float(motion.get("scale",1))
                c.rotate=float(motion.get("rotate",0))
                c.opacity=float(motion.get("opacity",1))
                c.update()
                # O asset raster não muda a cada estado. Evitar trocar ``src`` aqui
                # reduz decode/repaint e impede regressão para imagens maiores. O estado
                # continua perceptível pelos micro-movimentos até existir um pack real
                # de expressões distintas (Rive/WebP/sprites) aprovado.
                if phase == 7:
                    self.nex_state.set_state("wave")
                elif phase == 9:
                    self.nex_state.set_state(getattr(self,"nex_current_mood","idle"))
                for i, coin in enumerate(self.nex_coin_controls or []):
                    active = p in ((i+1)%6, (i+2)%6)
                    coin.opacity = 1 if active else 0.08
                    coin.offset = ft.Offset(0, -0.22 if active else 0.08)
                    coin.update()
            except Exception:
                pass


    async def nex_click_and_chat(self):
        """Easter egg curto: Nex pula do galho e então abre a conversa."""
        try:
            if self.nex_float_image is not None:
                self.nex_state.set_state("jump")
                if self.nex_float_control is not None:
                    self.nex_float_control.offset=ft.Offset(0,-0.10); self.nex_float_control.scale=1.06; self.nex_float_control.update()
                await asyncio.sleep(0.55)
        except Exception:
            pass
        self._go_nex_chat()


    def cloud_snapshot(self):
        """Assinatura leve dos dados visíveis para evitar redesenhar a tela sem mudança."""
        incomes = self.cloud.list_income(self.month)
        expenses = self.cloud.list_expenses(self.month)
        acquisitions = self.cloud.list_acquisitions(True)
        return (
            tuple(sorted((str(x["id"]), float(x["amount"]), x.get("note", "")) for x in incomes)),
            tuple(sorted((str(x["id"]), float(x["amount"]), x.get("description", ""), x.get("month", "")) for x in expenses)),
            tuple(sorted((str(x["id"]), float(x["estimated"]), float(x["saved"]), x.get("status", "")) for x in acquisitions)),
        )


    async def auto_sync_loop(self):
        # Atualiza a interface somente quando outro dispositivo realmente mudou os dados.
        while True:
            await asyncio.sleep(15)
            try:
                if not (self.cloud.user and self.cloud.household):
                    continue
                snapshot = await asyncio.to_thread(self.cloud_snapshot)
                now = datetime.now().strftime("%H:%M:%S")
                if self.last_cloud_snapshot is None:
                    self.last_cloud_snapshot = snapshot
                    self.last_sync = now
                elif snapshot != self.last_cloud_snapshot:
                    self.last_cloud_snapshot = snapshot
                    self.last_sync = now
                    if self.screen == 0:
                        self.render()
            except Exception as exc:
                logger.warning("sync_failed kind=%s", type(exc).__name__)


    def on_nav(self, e):
        self.screen = e.control.selected_index
        self.render()


    def nex_asset(self, mood="idle", role="hero"):
        """Asset canônico otimizado por contexto/tamanho.

        O estado controla movimento; a arte permanece no master aprovado enquanto
        não houver pack de expressões realmente distinto.
        """
        self.nex_state.set_state(mood)
        return self.nex_state.asset(role)


    def _nex_suggestion(self, data=None):
        data = data or self.dashboard_data()
        pending = float(data.get("pending_month") or 0)
        bal = float(data.get("balance") or 0)
        proj = float(data.get("projected_balance") or 0)
        if bal < 0:
            return ("worry", "Seu caixa está negativo. Vamos proteger o essencial primeiro.")
        if pending > 0 and proj < max(100, bal * 0.25):
            return ("thinking", f"Tem {brl(pending)} a vencer. Eu seguraria compras novas por enquanto.")
        if proj > 500:
            return ("celebrate", "Seu caixa está respirando. Bora manter o ritmo sem perder as próximas contas de vista.")
        return ("idle", "Tô acompanhando sua evolução. Pequenas escolhas, grandes conquistas.")


    def _desktop_sidebar(self):
        items = [
            (ft.Icons.HOME_OUTLINED, "Início", lambda: self._go_screen(0), lambda: self.screen == 0),
            (ft.Icons.SWAP_HORIZ, "Transações", lambda: self._go_movement_tab(0), lambda: self.screen == 1 and self.movement_tab in (0,1)),
            (ft.Icons.SHOPPING_BAG_OUTLINED, "Aquisições", lambda: self._go_movement_tab(2), lambda: self.screen == 1 and self.movement_tab == 2),
            (ft.Icons.SHOPPING_CART_OUTLINED, "Mercado", lambda: self._go_movement_tab(3), lambda: self.screen == 1 and self.movement_tab == 3),
            (ft.Icons.TRACK_CHANGES, "Planejamento", lambda: self._go_screen(2), lambda: self.screen == 2),
            (ft.Icons.AUTO_AWESOME_OUTLINED, "Nex", self._go_nex_chat, lambda: self.screen == 3 and self.assistant_tab == 1),
            (ft.Icons.SETTINGS_OUTLINED, "Mais", lambda: self._go_screen(4), lambda: self.screen == 4),
        ]
        buttons=[]
        for icon,label,action,is_active in items:
            active=bool(is_active())
            buttons.append(ft.Container(
                border_radius=14,
                bgcolor="#292654" if active else None,
                content=ft.ListTile(
                    leading=ft.Icon(icon,color="#8B7CFF" if active else self.muted_color()),
                    title=ft.Text(label,weight=ft.FontWeight.BOLD if active else None),
                    on_click=lambda e,fn=action:fn(),
                )
            ))
        try:
            mood,tip=self._nex_suggestion()
        except Exception:
            mood,tip=("idle","Precisando de mim?")
        nex=ft.Container(
            on_click=lambda e:self._go_nex_chat(),
            tooltip="Falar com o Nex",
            border_radius=18,
            padding=10,
            bgcolor="#17192B",
            border=ft.Border.all(1,"#393266"),
            content=ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=4,controls=[
                ft.Image(src=self.nex_asset(mood,"dock"),width=92,height=92,fit=ft.BoxFit.CONTAIN,gapless_playback=True),
                ft.Text("Nex",weight=ft.FontWeight.BOLD),
                ft.Text(tip,size=9,color=self.muted_color(),text_align=ft.TextAlign.CENTER,max_lines=3,overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text("Toque para conversar",size=8,color="#8B7CFF"),
            ])
        )
        return ft.Container(
            width=246,bgcolor="#0E111B" if self.is_dark() else "#F1F3FA",
            padding=ft.Padding.symmetric(horizontal=12,vertical=18),
            content=ft.Column(controls=[
                ft.Row(spacing=8,controls=[ft.Icon(ft.Icons.BAR_CHART_ROUNDED,color="#6D63FF",size=30),ft.Text("NexGrana",size=22,weight=ft.FontWeight.BOLD)]),
                ft.Text("Sua grana. Seu próximo nível.",size=10,color=self.muted_color()),
                ft.Divider(height=24),
                *buttons,
                ft.Container(expand=True),
                nex,
            ])
        )


    def _go_screen(self, idx):
        self.screen = idx
        if self.page.navigation_bar:
            self.page.navigation_bar.selected_index = idx
        self.render()


    def _go_movement_tab(self, idx):
        self.movement_tab = idx
        self._go_screen(1)


    def _go_nex_chat(self):
        self.assistant_tab = 1
        self._go_screen(3)


    def render(self):
        """Atualiza o host principal sem desmontar toda a árvore da página.

        A versão anterior usava ``page.clean()`` a cada navegação, gerando telas
        vazias perceptíveis e recriando controles/decodificando imagens. O host
        persistente mantém a janela estável; apenas o conteúdo interno troca.
        """
        if not self.cloud.user or not self.cloud.household:
            return
        builders = [self.dashboard, self.movements_screen, self.planning_screen, self.assistant_hub_screen, self.more_screen]
        with self.perf.measure(f"render_screen_{self.screen}"):
            content = builders[self.screen]()
            self.nex_float_control = None if self.screen != 0 else self.nex_float_control
            desktop = bool((self.page.width or 0) >= 900)
            if self.page.navigation_bar:
                self.page.navigation_bar.visible = not desktop
            if desktop:
                shell = ft.Row(expand=True, spacing=0, controls=[self._desktop_sidebar(), ft.Container(expand=True, content=content)])
            else:
                shell = content
            if self.root_host is None:
                self.root_host = ft.Container(expand=True, content=shell)
                self.root_safe_area = ft.SafeArea(expand=True, content=self.root_host)
                self.page.clean()
                self.page.add(self.root_safe_area)
            else:
                self.root_host.content = shell
            self.page.update()


    def header(self, title, subtitle=""):
        # 0.15.0: cabeçalho fluido. Perfil e mês nunca são empurrados para fora da tela.
        bucket = self._layout_bucket()
        phone = bucket == "phone"
        compact = bucket in ("phone", "tablet", "compact")
        identity = ft.Column(spacing=1, controls=[
            ft.Text(title, size=20 if phone else 24, weight=ft.FontWeight.BOLD, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            ft.Text(subtitle, size=10 if phone else 11, color=self.muted_color(), max_lines=2 if compact else 1, overflow=ft.TextOverflow.ELLIPSIS),
        ])
        month_row = ft.Row(
            expand=True,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            spacing=0,
            controls=[
                ft.IconButton(ft.Icons.CHEVRON_LEFT, tooltip="Mês anterior", on_click=lambda e: self.change_month(-1)),
                ft.Container(expand=True, alignment=ft.Alignment.CENTER, content=ft.Text(month_label(self.month), size=12 if phone else 13, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)),
                ft.IconButton(ft.Icons.CHEVRON_RIGHT, tooltip="Próximo mês", on_click=lambda e: self.change_month(1)),
            ],
        )
        sync = ft.Text((f"☁ sincronizado {self.last_sync}" if getattr(self.cloud,"online",True) else "◌ offline • último cache"), size=9, color=ft.Colors.GREEN_700 if getattr(self.cloud,"online",True) else ft.Colors.ORANGE_700)
        profile = self.profile_selector(compact=True)
        if phone:
            controls = [
                identity,
                ft.ResponsiveRow(spacing=6, run_spacing=6, controls=[
                    ft.Container(col=12, content=profile),
                    ft.Container(col=12, content=month_row),
                ]),
                ft.Row(alignment=ft.MainAxisAlignment.END, controls=[sync]),
            ]
            content = ft.Column(spacing=6, controls=controls)
        elif compact:
            content = ft.Column(spacing=6, controls=[
                identity,
                ft.Row(spacing=8, controls=[ft.Container(width=165, content=profile), ft.Container(expand=True, content=month_row)]),
                ft.Row(alignment=ft.MainAxisAlignment.END, controls=[sync]),
            ])
        else:
            content = ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.START, controls=[
                ft.Container(expand=True, content=identity),
                ft.Container(width=430, content=ft.Column(horizontal_alignment=ft.CrossAxisAlignment.END, spacing=4, controls=[
                    ft.Row(spacing=8, controls=[ft.Container(width=165, content=profile), ft.Container(expand=True, content=month_row)]), sync
                ])),
            ])
        return ft.Container(bgcolor=self.surface_color(), padding=ft.Padding.symmetric(horizontal=14, vertical=10), content=content)


    def members(self):
        return self.cloud.list_members()


    def member_options(self):
        return [ft.DropdownOption(key=str(m["id"]), text=m["display_name"]) for m in self.members()]


    def active_member(self):
        members = self.members()
        if self.active_member_id:
            for m in members:
                if str(m.get("id")) == str(self.active_member_id):
                    return m
        uid = str(self.cloud.user.id) if self.cloud.user else ""
        for m in members:
            if str(m.get("user_id")) == uid:
                return m
        return members[0] if members else None


    def current_member(self):
        # Perfil ativo também vira o pagador/pessoa padrão nos novos lançamentos.
        return self.active_member()


    def set_active_member(self, member_id):
        if member_id and str(member_id) not in {str(m["id"]) for m in self.members()}:
            self.snack("Perfil indisponível nesta família.", True)
            return
        self.active_member_id = str(member_id or "") or None
        if self.active_member_id:
            self.preferences["active_member_id"] = self.active_member_id
        else:
            self.preferences.pop("active_member_id", None)
        self.save_preferences()
        self.chat_messages.clear()
        self.chat_pending = None
        self.chat_context = None
        self.chat_aliases.clear()
        self.chat_memory = {"last_topic": None, "last_user_mood": None, "last_intent": None}
        self.receipt_photos.clear()
        self.extra_income_journeys = self.cloud.list_journeys(self.active_member_id)
        self.extra_income_path = self.cloud.load_journey_progress(self.active_member_id)
        self.render()


    def profile_selector(self, compact=False):
        members = self.members()
        active = self.active_member()
        if not members:
            return ft.Container()
        return ft.Dropdown(
            label="Perfil" if not compact else None,
            value=str(active.get("id")) if active else str(members[0].get("id")),
            options=[ft.DropdownOption(key=str(m.get("id")), text=m.get("display_name") or "Pessoa") for m in members],
            width=150 if compact else 180,
            dense=True,
            text_size=11,
            on_select=lambda e: self.set_active_member(e.control.value),
        )


    def _section_tabs(self, labels, selected, setter):
        controls=[]
        for i,label in enumerate(labels):
            controls.append(ft.Button(
                label,
                on_click=lambda e, idx=i: setter(idx),
                style=ft.ButtonStyle(
                    bgcolor=ft.Colors.INDIGO if i == selected else self.surface_alt_color(),
                    color=ft.Colors.WHITE if i == selected else None,
                ),
            ))
        return ft.Container(
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            bgcolor=self.page_color(),
            content=ft.Row(controls=controls, wrap=True, spacing=8),
        )


    def set_movement_tab(self, idx):
        self.movement_tab=idx
        self.render()


    def movements_screen(self):
        body=[self.income_screen, self.expenses_screen, self.acquisitions_screen, self.market_screen][self.movement_tab]()
        desktop = bool((self.page.width or 0) >= 900)
        controls=[]
        if desktop:
            # No desktop Aquisições e Mercado ganham rotas próprias na sidebar.
            # Renda/Despesas continuam agrupadas como Transações.
            if self.movement_tab in (0,1):
                controls.append(self._section_tabs(["Renda", "Despesas"], self.movement_tab, self.set_movement_tab))
        else:
            # No celular economizamos espaço mantendo as quatro áreas juntas.
            controls.append(self._section_tabs(["Renda", "Despesas", "Aquisições", "Mercado"], self.movement_tab, self.set_movement_tab))
        controls.append(ft.Container(expand=True, content=body))
        return ft.Column(expand=True, spacing=0, controls=controls)


    def set_assistant_tab(self, idx):
        self.assistant_tab=idx
        self.render()


    def assistant_hub_screen(self):
        body=[self.assistant_screen, self.chat_screen, self.extra_income_screen][self.assistant_tab]()
        return ft.Column(expand=True, spacing=0, controls=[
            self._section_tabs(["Análises", "Nex", "Renda extra"], self.assistant_tab, self.set_assistant_tab),
            ft.Container(expand=True, content=body),
        ])


    async def open_external_url(self, url):
        try:
            await ft.UrlLauncher().launch_url(url, mode=ft.LaunchMode.EXTERNAL_APPLICATION)
        except Exception as ex:
            self.snack(f"Não foi possível abrir o link: {ex}", True)


    def logout(self, e=None):
        self.cloud.sign_out()
        self.page.navigation_bar = None
        self.chat_messages.clear()
        self.chat_pending = self.chat_context = None
        self.chat_aliases.clear()
        self.extra_income_path.clear()
        self.receipt_photos.clear()
        self.active_member_id = None
        self.preferences.pop("active_member_id",None)
        self.save_preferences()
        self.nex_float_control = self.nex_float_image = None
        self.nex_coin_controls = []
        self.root_host = None
        self.root_safe_area = None
        self._last_render_signature = None
        self._nex_chat_runtime = {}
        self.render_entry()



if __name__ == "__main__":
    import flet as ft
    from app import bootstrap
    ft.run(bootstrap)
