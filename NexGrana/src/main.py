from screens.home import HomeScreen
from screens.movements import MovementsScreen
from screens.acquisitions import AcquisitionsScreen
from screens.planning import PlanningScreen
from screens.market import MarketScreen
from screens.nex import NexScreen
from screens.analysis import AnalysisScreen
from screens.extra_income import ExtraIncomeScreen
from screens.investments import InvestmentsScreen
from screens.settings import SettingsScreen
from screens.tutorial import TutorialScreen
from screens.auth import AuthScreen
from ui.theme import ThemeScreen
from services.performance import PerformanceMonitor
from services.analytics import AnalyticsAdapter
from services.nex_conversation import AssistantPreferences, ChatScope
from ui.common import Cloud, NexEngine, NexEvent, NexStateMachine, ReauthenticationRequired, SessionUnavailable, add_months, asyncio, brl, bucket, datetime, ft, is_family_mode, logger, month_key, month_label, space_label, storage_dir

class NexGranaCloud(HomeScreen,MovementsScreen,AcquisitionsScreen,PlanningScreen,MarketScreen,NexScreen,AnalysisScreen,ExtraIncomeScreen,InvestmentsScreen,TutorialScreen,SettingsScreen,AuthScreen,ThemeScreen):
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
        self.planning_tab = 0
        self.expense_person_filter = "Todos"
        self.expense_order = "recent"
        self.expense_group = False
        self.preferences_path = storage_dir() / "preferences.json"
        self.preferences = self.load_preferences()
        self.active_member_id = self.preferences.get("active_member_id")
        self.nex_float_control = None
        self.nex_float_image = None
        self.nex_chat_live_control = None
        self.nex_coin_controls = []
        self.last_layout_bucket = None
        self.chat_memory = {"last_topic": None, "last_user_mood": None, "last_intent": None}
        self.conversation_id = "free"
        self._loaded_chat_scope = None
        self._conversation_store_memory = {}
        self.extra_income_path = {}
        self.extra_income_journeys = []
        self.nex_engine = NexEngine(self)
        self.nex_state = NexStateMachine(self.preferences.get("nex_vivo"))
        self.receipt_photos = []
        self.nex_last_hint = None
        self.page.on_resize = self.on_page_resized
        self.nex_action_label = None
        self.nex_motion_phase = 0
        self.nex_animation_started = False
        self.page.title = "NexGrana 0.24.0 QA"
        self.perf = PerformanceMonitor()
        self.analytics = AnalyticsAdapter(enabled=False)
        self.root_host = None
        self.root_safe_area = None
        self._last_render_signature = None
        self._members_cache = []
        self._handling_session_error = False
        self._tutorial_offer_shown = False
        self._nex_return_screen = 0
        self._tutorial_return_screen = 0
        self._tutorial_session_state = None
        self._nex_session_preferences = {}
        self._nex_session_generation = 0
        self._nex_active_request_id = None
        self._nex_active_scope = None
        self.page.theme_mode = ft.ThemeMode.DARK if self.preferences.get("dark_mode", True) else ft.ThemeMode.LIGHT
        self.apply_theme()
        self.page.bgcolor = self.page_color()
        self.page.padding = 0
        self.page.adaptive = True
        self.render_entry()


    def _layout_bucket(self):
        return bucket(self.page.width)


    def is_family_space(self):
        return is_family_mode(getattr(self.cloud, "household", None))


    def space_copy(self, individual, family):
        return space_label(getattr(self.cloud, "household", None), individual, family)


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
                # The device-level legacy light/dark choice cannot leak into a
                # different signed-in account. Authenticated styles are scoped.
                return self.cloud.vault.read("preferences:" + self.cloud._scope(), {})
        except (OSError, ValueError):
            logger.warning("preferences_read_failed")
        return theme


    def save_preferences(self):
        import json
        vault=getattr(self.cloud,"vault",None)
        if self.cloud.user and self.cloud.household and vault:
            vault.write("preferences:" + self.cloud._scope(), self.preferences)
        elif not self.cloud.user:
            self.preferences_path.write_text(json.dumps({"dark_mode": self.preferences.get("dark_mode", True)}), encoding="utf-8")


    def nex_preferences(self):
        stored = self.preferences.get("nex_preferences")
        merged = {**(stored if isinstance(stored, dict) else {}), **self._nex_session_preferences}
        return AssistantPreferences.from_mapping(merged).public_payload()


    def nex_user_name(self):
        return self.nex_preferences().get("preferred_name") or ""


    def set_nex_preferred_name(self, name, remember=False):
        current = AssistantPreferences.from_mapping({**self.nex_preferences(), "preferred_name": name, "remember": remember})
        values = current.public_payload()
        self._nex_session_preferences = values
        if remember:
            self.preferences["nex_preferences"] = values
            self.save_preferences()


    def forget_nex_preferred_name(self):
        self._nex_session_preferences = {**self.nex_preferences(), "preferred_name": "", "remember": False}
        saved = dict(self.preferences.get("nex_preferences") or {})
        saved.update({"preferred_name": "", "remember": False})
        self.preferences["nex_preferences"] = saved
        self.save_preferences()


    def change_month(self, offset):
        target_month = add_months(self.month, offset)
        if offset > 0 and self.month_close_needed(self.month):
            self.close_month_dialog(self.month, continue_to=target_month)
            return
        self.month = target_month
        self.last_cloud_snapshot = None
        self.render()

    def confirm_historical_entry(self, entry_type, entry_date, on_confirm):
        """Make the selected competence explicit before saving a backdated row."""
        target_month = entry_date.strftime("%m/%Y")
        selected_month = self.month
        tm, ty = map(int, target_month.split("/"))
        sm, sy = map(int, selected_month.split("/"))
        if (ty, tm) >= (sy, sm):
            on_confirm()
            return

        dialog = ft.AlertDialog(
            title=ft.Text("Lançamento em mês anterior"),
            content=ft.Text(
                f"A data informada coloca esta {entry_type} em {month_label(target_month)}, "
                f"mesmo com {month_label(selected_month)} aberto na tela. Se esse mês já foi fechado, "
                "o Nex manterá o lançamento na data correta e recalculará o saldo transportado. Confirma?",
                size=12,
            ),
        )

        def confirm(_):
            self.page.pop_dialog()
            on_confirm()

        dialog.actions = [
            ft.TextButton("Voltar e revisar", on_click=lambda e: self.page.pop_dialog()),
            ft.Button(f"Salvar em {month_label(target_month)}", icon=ft.Icons.CHECK, on_click=confirm),
        ]
        self.page.show_dialog(dialog)


    def snack(self, text, error=False):
        text = str(text or "")
        if error and any(marker in text for marker in ("Traceback", "APIError", "PGRST", "site-packages", "File \"", "C:\\", "/workspace/", "{'message'")):
            text = "Não foi possível concluir agora. Tente novamente; se persistir, confira a conexão e a migração do banco."
        self.page.show_dialog(
            ft.SnackBar(
                ft.Text(text),
                bgcolor=ft.Colors.RED_700 if error else ft.Colors.GREEN_700,
            )
        )


    def start_app(self):
        self._nex_session_generation += 1
        self._nex_active_request_id = None
        self._nex_active_scope = None
        self.nex_busy = False
        self._nex_chat_runtime = {}
        self.preferences = self.load_preferences()
        self.page.theme_mode = ft.ThemeMode.DARK if self.preferences.get("dark_mode", True) else ft.ThemeMode.LIGHT
        self.apply_theme()
        self.nex_state.configure(self.preferences.get("nex_vivo"))
        self.active_member_id = self.preferences.get("active_member_id")
        self.page.clean()
        self.root_host = None
        self.root_safe_area = None
        self.screen = 0
        try:
            self._members_cache = list(self.cloud.list_members())
        except ReauthenticationRequired:
            self.show_session_expired()
            return
        except SessionUnavailable:
            self.page.add(self.error_screen(
                "Sem conexão para validar sua sessão",
                "Seus dados locais continuam protegidos. Conecte-se à internet e tente novamente.",
                show_logout=True,
            ))
            return
        selected=self.active_member()
        if selected:
            self.active_member_id=str(selected.get("id"))
            self.preferences["active_member_id"]=self.active_member_id
            self.save_preferences()
        try:
            self.extra_income_journeys = self.cloud.list_journeys(self.active_member_id)
            self.extra_income_path = self.cloud.load_journey_progress(self.active_member_id)
        except ReauthenticationRequired:
            self.show_session_expired()
            return
        except SessionUnavailable:
            self.extra_income_journeys = []
            self.extra_income_path = {}
        except Exception as exc:
            logger.warning("journey_bootstrap_failed kind=%s",type(exc).__name__)
            self.extra_income_journeys = []
            self.extra_income_path = {}
        self.page.navigation_bar = ft.NavigationBar(
            selected_index=0,
            on_change=self.on_nav,
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.HOME_OUTLINED, selected_icon=ft.Icons.HOME, label="Início"),
                ft.NavigationBarDestination(icon=ft.Icons.SWAP_HORIZ, selected_icon=ft.Icons.SWAP_HORIZ, label="Transações"),
                ft.NavigationBarDestination(icon=ft.Icons.TRACK_CHANGES, label="Planejamento"),
                ft.NavigationBarDestination(icon=ft.Icons.SHOPPING_CART_OUTLINED, selected_icon=ft.Icons.SHOPPING_CART, label="Mercado"),
                ft.NavigationBarDestination(icon=ft.Icons.AUTO_AWESOME_OUTLINED, selected_icon=ft.Icons.AUTO_AWESOME, label="Nex"),
            ],
        )
        self.render()
        if not self.show_profile_gate():
            self.show_tutorial_offer()
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
                # Na tela do chat, anima o Nex daquela tela. Em outras rotas,
                # usa o personagem do painel inicial. Controles antigos podem
                # continuar referenciados após um render e não devem vencer.
                c = self.nex_chat_live_control if self.screen == 4 else self.nex_float_control
                if c is None:
                    continue
                phase = (phase + 1) % 120
                p = phase % 6
                # Let a real event finish before returning to rest. The old
                # 7/9-second idle overwrite hid celebrations and chat reactions.
                self.nex_state.settle()
                if phase == (60 if self.nex_state.settings.intensity == "animated" else 119):
                    self.nex_state.handle(NexEvent.USER_IDLE,cooldown_seconds=60)
                motion=self.nex_state.motion(phase)
                c.offset=ft.Offset(float(motion.get("dx",0)),float(motion.get("dy",0)))
                c.scale=float(motion.get("scale",1))
                c.rotate=float(motion.get("rotate",0))
                c.opacity=float(motion.get("opacity",1))
                c.update()
                # O asset raster não muda a cada estado. Evitar trocar ``src`` aqui
                # reduz decode/repaint e impede regressão para imagens maiores. O estado
                # continua perceptível pelos micro-movimentos até existir um pack real
                # de expressões distintas (Rive/WebP/sprites) aprovado.
                for i, coin in enumerate(self.nex_coin_controls or []):
                    if (not self.nex_state.settings.enabled or not self.nex_state.settings.effects
                            or self.nex_state.settings.reduced_motion or self.nex_state.state.value == "idle"):
                        coin.opacity=0
                        coin.update()
                        continue
                    active = p in ((i+1)%6, (i+2)%6)
                    coin.opacity = 1 if active else 0.08
                    coin.offset = ft.Offset(0, -0.22 if active else 0.08)
                    coin.update()
            except Exception:
                pass


    async def nex_click_and_chat(self):
        """Easter egg curto: Nex pula do galho e então abre a conversa."""
        try:
            self.nex_state.click()
            if self.nex_float_image is not None:
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
        # A navegação lê a cópia cifrada local. A rede atualiza essa cópia aqui,
        # fora do gesto do usuário, para que conexão mediana não congele a tela.
        retry_seconds = 2
        while True:
            try:
                if not (self.cloud.user and self.cloud.household):
                    await asyncio.sleep(2)
                    continue
                await asyncio.to_thread(self.cloud.sync_pending_consents)
                changed = await asyncio.to_thread(self.cloud.refresh_core_data)
                snapshot = await asyncio.to_thread(self.cloud_snapshot)
                now = datetime.now().strftime("%H:%M:%S")
                if self.last_cloud_snapshot is None:
                    self.last_cloud_snapshot = snapshot
                    self.last_sync = now
                elif changed or snapshot != self.last_cloud_snapshot:
                    self.last_cloud_snapshot = snapshot
                    self.last_sync = now
                    if self.screen == 0:
                        self.render()
                self.cloud.online = True
                retry_seconds = 2
                await asyncio.sleep(15)
            except Exception as exc:
                logger.warning("sync_failed kind=%s", type(exc).__name__)
                self.cloud.online = False
                await asyncio.sleep(retry_seconds)
                retry_seconds = min(60, retry_seconds * 2)


    def on_nav(self, e):
        next_screen=e.control.selected_index
        if self.screen==4 and next_screen!=4:
            self._nex_chat_runtime={}
        self.screen = next_screen
        self.render()


    def nex_asset(self, mood="idle", role="hero", context=None):
        """Asset canônico otimizado por contexto/tamanho.

        O estado controla movimento; a arte permanece no master aprovado enquanto
        não houver pack de expressões realmente distinto.
        """
        from services.nex_skins import skin_asset
        return skin_asset(self.preferences, role=role, context=context) or self.nex_state.asset(role)


    def nex_event(self, event, context=None, notify=False):
        """Entrega um evento de UX ao Nex sem tocar na lógica financeira."""
        reaction = self.nex_state.handle(event, context or {})
        if notify and reaction.accepted and reaction.speech:
            self.snack(reaction.speech)
        return reaction


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
            (ft.Icons.TRACK_CHANGES, "Planejamento", lambda: self._go_screen(2), lambda: self.screen == 2),
            (ft.Icons.SHOPPING_CART_OUTLINED, "Mercado", lambda: self._go_market_tab("Compras"), lambda: self.screen == 3 and getattr(self,"_market_tab","Compras")=="Compras"),
            (ft.Icons.LOCAL_OFFER_OUTLINED, "Achados", lambda: self._go_market_tab("Achados"), lambda: self.screen == 3 and getattr(self,"_market_tab","Compras")=="Achados"),
            (ft.Icons.AUTO_AWESOME_OUTLINED, "Nex", self._go_nex_chat, lambda: self.screen == 4),
            (ft.Icons.SETTINGS_OUTLINED, "Mais", lambda: self._go_screen(5), lambda: self.screen == 5),
        ]
        buttons=[]
        for icon,label,action,is_active in items:
            active=bool(is_active())
            buttons.append(ft.Container(
                border_radius=14,
                bgcolor="#35247E" if active and self.is_dark() else (self.surface_alt_color() if active else None),
                border=ft.Border.all(1,"#7459FF" if active else self.border_color()) if active else None,
                content=ft.ListTile(
                    leading=ft.Icon(icon,color="#B99BFF" if active and self.is_dark() else (self.visual_style()["accent"] if active else self.muted_color())),
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
            bgcolor=self.surface_color(),
            border=ft.Border.all(1,self.border_color()),
            content=ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=4,controls=[
                ft.Image(src=self.nex_asset(mood,"dock"),width=92,height=92,fit=ft.BoxFit.CONTAIN,gapless_playback=True),
                ft.Text("Nex",weight=ft.FontWeight.BOLD),
                ft.Text(tip,size=9,color=self.muted_color(),text_align=ft.TextAlign.CENTER,max_lines=3,overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text("Toque para conversar",size=8,color="#8B7CFF"),
            ])
        )
        return ft.Container(
            width=246,bgcolor="#0A1025" if self.is_dark() else "#F1F3FA",
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
        if self.screen==4 and idx!=4:
            self._nex_chat_runtime={}
        self.screen = idx
        if self.page.navigation_bar and 0 <= idx <= 4:
            self.page.navigation_bar.selected_index = idx
        self.render()

    def _go_market_tab(self, tab="Compras"):
        self._market_tab=tab
        self._go_screen(3)


    def _go_movement_tab(self, idx):
        self.movement_tab = idx
        self._go_screen(1)


    def _go_nex_chat(self):
        if self.screen != 4:
            self._nex_return_screen = self.screen
        self._go_screen(4)

    def _go_tutorial(self, module="welcome"):
        if self.screen != 6:
            self._tutorial_return_screen = self.screen if self.screen in range(0,6) else 0
        try:
            self.tutorial_session().start(module)
            self._save_tutorial_progress()
        except ValueError:
            self.tutorial_session().start("welcome")
        self.screen=6
        self.render()

    def _back_from_nex(self):
        target = self._nex_return_screen if self._nex_return_screen in range(0, 5) else 0
        self._go_screen(target)


    def render(self):
        """Atualiza o host principal sem desmontar toda a árvore da página.

        A versão anterior usava ``page.clean()`` a cada navegação, gerando telas
        vazias perceptíveis e recriando controles/decodificando imagens. O host
        persistente mantém a janela estável; apenas o conteúdo interno troca.
        """
        if not self.cloud.user or not self.cloud.household:
            return
        builders = [self.dashboard, self.movements_screen, self.planning_screen, self.market_screen, self.chat_screen, self.more_screen, self.tutorial_screen]
        try:
            with self.perf.measure(f"render_screen_{self.screen}"):
                content = builders[self.screen]()
        except ReauthenticationRequired:
            self.show_session_expired()
            return
        except SessionUnavailable:
            self.snack("Sem conexão para renovar a sessão. Confira a internet e tente novamente.", True)
            return
        except Exception as exc:
            logger.warning("screen_render_failed screen=%s kind=%s",self.screen,type(exc).__name__)
            content=self.error_screen(
                "Não foi possível abrir esta tela",
                "Tente novamente. Se o problema persistir, confira a conexão e se a migração 0.20 foi aplicada.",
            )
        self.nex_float_control = None if self.screen != 0 else self.nex_float_control
        desktop = bool((self.page.width or 0) >= 900)
        if self.page.navigation_bar:
            self.page.navigation_bar.visible = not desktop and self.screen != 6
        if desktop and self.screen != 6:
            shell = ft.Row(expand=True, spacing=0, controls=[self._desktop_sidebar(), ft.Container(expand=True, content=content)])
        else:
            # O tutorial ocupa a janela inteira também no notebook/desktop.
            # Isso evita a coluna lateral competir com a experiência guiada.
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
        try:
            sync_summary=self.cloud.sync_summary()
        except Exception:
            sync_summary={"queued":0,"conflict":0,"rejected":0,"total":0}
        if sync_summary["conflict"]:
            sync_text=f"⚠ {sync_summary['conflict']} conflito(s) para revisar"
            sync_color=ft.Colors.RED_400
        elif sync_summary["rejected"]:
            sync_text=f"⚠ {sync_summary['rejected']} alteração(ões) recusada(s)"
            sync_color=ft.Colors.RED_400
        elif sync_summary["queued"]:
            sync_text=f"↻ {sync_summary['queued']} alteração(ões) pendente(s)"
            sync_color=ft.Colors.ORANGE_700
        elif getattr(self.cloud,"online",True):
            sync_text=f"☁ sincronizado {self.last_sync}"
            sync_color=ft.Colors.GREEN_700
        else:
            sync_text="◌ offline • dados locais"
            sync_color=ft.Colors.ORANGE_700
        sync = ft.Text(sync_text,size=9,color=sync_color)
        profile = self.profile_selector(compact=True)
        mobile_identity = ft.Row(controls=[
            ft.Container(expand=True, content=identity),
            ft.IconButton(ft.Icons.SETTINGS_OUTLINED, tooltip="Mais opções", on_click=lambda e:self._go_screen(5)),
        ])
        if phone:
            controls = [
                mobile_identity,
                ft.ResponsiveRow(spacing=6, run_spacing=6, controls=[
                    ft.Container(col=12, content=profile),
                    ft.Container(col=12, content=month_row),
                ]),
                ft.Row(alignment=ft.MainAxisAlignment.END, controls=[sync]),
            ]
            content = ft.Column(spacing=6, controls=controls)
        elif compact:
            content = ft.Column(spacing=6, controls=[
                mobile_identity,
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
        if self._members_cache:
            return list(self._members_cache)
        rows = list(self.cloud.list_members())
        self._members_cache = rows
        return list(rows)


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
        self._nex_session_generation += 1
        self._nex_active_request_id = None
        self._nex_active_scope = None
        self.nex_busy = False
        self._nex_chat_runtime={}
        if self.active_member_id:
            self.preferences["active_member_id"] = self.active_member_id
        else:
            self.preferences.pop("active_member_id", None)
        self.save_preferences()
        self.chat_messages.clear()
        self.conversation_id = "free"
        self._loaded_chat_scope = None
        self.chat_pending = None
        self.chat_context = None
        self.chat_aliases.clear()
        self.chat_memory = {"last_topic": None, "last_user_mood": None, "last_intent": None}
        self.receipt_photos.clear()
        self.extra_income_journeys = self.cloud.list_journeys(self.active_member_id)
        self.extra_income_path = self.cloud.load_journey_progress(self.active_member_id)
        self.render()


    def show_session_expired(self):
        """Sai do shell financeiro sem expor traceback ou caminhos internos."""
        if self._handling_session_error:
            return
        self._handling_session_error = True
        try:
            self._nex_session_generation += 1
            self._nex_active_request_id = None
            self._nex_active_scope = None
            self.nex_busy = False
            self._nex_chat_runtime = {}
            self.page.navigation_bar = None
            self.root_host = None
            self.root_safe_area = None
            self._members_cache = []
            self.chat_messages.clear()
            self.chat_pending = self.chat_context = None
            self.page.clean()
            self.page.add(self.session_expired_screen())
            self.page.update()
        finally:
            self._handling_session_error = False


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

    def show_profile_gate(self):
        """Choose a financial view after login for a family with multiple profiles.

        The selection affects the active view, never the authenticated identity
        or database authorization. Individual spaces skip the extra step.
        """
        members=self.members()
        if len(members)<2 or (self.cloud.household or {}).get('mode')!='family':
            return False
        from services.nex_skins import skin_asset
        icon=skin_asset(self.preferences) or 'nex/nex_avatar.png'
        def choose(member):
            self.page.pop_dialog()
            self.set_active_member(member['id'])
            self.show_tutorial_offer()
        choices=[ft.Container(
            col={"xs":6,"sm":4},padding=12,border_radius=16,bgcolor=self.surface_alt_color(),
            border=ft.Border.all(1,self.border_color()),
            on_click=lambda e,m=member:choose(m),
            content=ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=6,controls=[
                ft.Image(src=icon,width=76,height=76,fit=ft.BoxFit.CONTAIN),
                ft.Text(member.get('display_name') or 'Pessoa',weight=ft.FontWeight.BOLD,text_align=ft.TextAlign.CENTER),
            ]),
        ) for member in members]
        width,height=self.dialog_dimensions(620,490)
        self.page.show_dialog(ft.AlertDialog(
            title=ft.Text('Quem vai usar o NexGrana?'),
            content=ft.Column(width=width,height=height,scroll=ft.ScrollMode.AUTO,controls=[
                ft.Text('Escolha o perfil financeiro para esta sessão. A conta conectada e suas permissões continuam as mesmas.',size=11),
                ft.ResponsiveRow(spacing=8,run_spacing=8,controls=choices),
            ]),
        ))
        return True


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
        if self.movement_tab not in (0,1):
            self.movement_tab = 0
        body=[self.income_screen, self.expenses_screen][self.movement_tab]()
        controls=[self._section_tabs(["Renda", "Despesas"], self.movement_tab, self.set_movement_tab)]
        controls.append(ft.Container(expand=True, content=body))
        return ft.Column(expand=True, spacing=0, controls=controls)


    def set_assistant_tab(self, idx):
        self.assistant_tab=idx
        self.render()


    def assistant_hub_screen(self):
        """Alias de compatibilidade: Nex agora abre diretamente no chat."""
        return self.chat_screen()


    async def open_external_url(self, url):
        try:
            await ft.UrlLauncher().launch_url(url, mode=ft.LaunchMode.EXTERNAL_APPLICATION)
        except Exception as ex:
            self.snack(f"Não foi possível abrir o link: {ex}", True)


    def logout(self, e=None):
        self._nex_session_generation += 1
        self._nex_active_request_id = None
        self._nex_active_scope = None
        self.nex_busy = False
        self._nex_session_preferences = {}
        self.cloud.sign_out()
        self.page.navigation_bar = None
        self.chat_messages.clear()
        self.conversation_id = "free"
        self._loaded_chat_scope = None
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
        self._tutorial_session_state = None
        self._members_cache = []
        self.render_entry()



if __name__ == "__main__":
    import flet as ft
    from app import bootstrap
    ft.run(bootstrap)
