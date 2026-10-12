import asyncio
import logging

from httpx import TransportError
from ui.common import ReauthenticationRequired, SessionUnavailable, ft, load_config, save_config

logger = logging.getLogger(__name__)

class AuthScreen:
    def render_entry(self):
        self.page.clean()

        if not self.cloud.configured():
            self.page.add(self.setup_cloud_screen())
            return

        try:
            self.cloud.connect()
        except Exception:
            self.page.add(
                self.error_screen(
                    "O primeiro acesso precisa de internet",
                    "Conecte-se para validar sua conta e carregar seu espaço pela primeira vez. Depois, o NexGrana pode abrir offline os dados que já foram salvos com segurança neste aparelho.",
                )
            )
            return

        try:
            user = self.cloud.current_user()
        except ReauthenticationRequired:
            self.page.add(self.session_expired_screen())
            return
        except SessionUnavailable:
            self.page.add(self.error_screen(
                "Sem conexão para validar sua sessão",
                "Conecte-se à internet e tente novamente. Sua sessão local não foi apagada.",
                show_logout=True,
            ))
            return
        except Exception:
            user = None

        if not user:
            self.page.add(self.auth_screen())
            return

        # Usuário autenticado. O contexto financeiro é carregado separadamente
        # para não mascarar um login válido.
        try:
            self.cloud.load_context()
        except ReauthenticationRequired:
            self.page.add(self.session_expired_screen())
            return
        except SessionUnavailable:
            self.page.add(self.error_screen(
                "Sem conexão para carregar sua conta",
                "Conecte-se à internet e tente novamente. Seus dados não foram apagados.",
                show_logout=True,
            ))
            return
        except Exception:
            self.page.add(
                self.error_screen(
                    "Login realizado, mas houve erro ao carregar sua conta",
                    "Não foi possível abrir os dados agora. Tente novamente; se persistir, confira se a migração do banco foi aplicada.",
                    show_logout=True,
                )
            )
            return

        if not self.cloud.household:
            self.page.add(self.workspace_screen())
        else:
            self.start_app()


    def error_screen(self, title, detail, show_logout=False):
        buttons = [
            ft.Button(
                "Tentar novamente",
                icon=ft.Icons.REFRESH,
                on_click=lambda e: self.render_entry(),
            )
        ]

        if show_logout:
            buttons.append(
                ft.OutlinedButton(
                    "Sair",
                    icon=ft.Icons.LOGOUT,
                    on_click=self.logout,
                )
            )

        return ft.SafeArea(
            expand=True,
            content=ft.Container(
                alignment=ft.Alignment.CENTER,
                padding=20,
                content=ft.Container(
                    width=620,
                    padding=28,
                    bgcolor=self.surface_color(),
                    border_radius=24,
                    border=ft.Border.all(1, ft.Colors.RED_100),
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=12,
                        controls=[
                            ft.Icon(
                                ft.Icons.ERROR_OUTLINE,
                                size=52,
                                color=ft.Colors.RED_600,
                            ),
                            ft.Text(
                                title,
                                size=22,
                                weight=ft.FontWeight.BOLD,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Text(
                                detail,
                                selectable=True,
                                color=ft.Colors.RED_700,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Row(
                                alignment=ft.MainAxisAlignment.CENTER,
                                controls=buttons,
                            ),
                        ],
                    ),
                ),
            ),
        )


    def session_expired_screen(self):
        return ft.SafeArea(
            expand=True,
            content=ft.Container(
                alignment=ft.Alignment.CENTER,
                padding=20,
                content=ft.Container(
                    width=560,
                    padding=28,
                    bgcolor=self.surface_color(),
                    border_radius=24,
                    border=ft.Border.all(1, self.border_color()),
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=12,
                        controls=[
                            ft.Icon(ft.Icons.LOCK_CLOCK_OUTLINED, size=52, color="#8B7CFF"),
                            ft.Text("Sua sessão expirou", size=22, weight=ft.FontWeight.BOLD, text_align=ft.TextAlign.CENTER),
                            ft.Text(
                                "Entre novamente para proteger seus dados e continuar de onde parou.",
                                color=self.muted_color(),
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Button(
                                "Entrar novamente",
                                icon=ft.Icons.LOGIN,
                                on_click=lambda e: self.render_entry(),
                            ),
                        ],
                    ),
                ),
            ),
        )


    def setup_cloud_screen(self):
        cfg = load_config()
        url = ft.TextField(label="Supabase Project URL", value=cfg.get("url", ""), width=520)
        key = ft.TextField(label="Supabase anon/publishable key", value=cfg.get("anon_key", ""), password=True, can_reveal_password=True, width=520)

        def save(e):
            if not url.value.strip() or not key.value.strip():
                self.snack("Preencha URL e chave do Supabase.", True)
                return
            save_config(url.value, key.value)
            try:
                self.cloud.connect()
                self.snack("Nuvem configurada.")
                self.render_entry()
            except Exception:
                self.snack("Não foi possível conectar. Confira a URL, a chave pública e sua internet.", True)

        return ft.SafeArea(
            expand=True,
            content=ft.Container(
                alignment=ft.Alignment.CENTER,
                padding=20,
                content=ft.Container(
                    width=620,
                    padding=28,
                    bgcolor=self.surface_color(),
                    border_radius=24,
                    border=ft.Border.all(1, self.border_color()),
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=14,
                        controls=[
                            ft.Icon(ft.Icons.CLOUD_SYNC, size=58, color=ft.Colors.INDIGO),
                            ft.Text("NexGrana 0.24.0 QA", size=28, weight=ft.FontWeight.BOLD),
                            ft.Text(
                                "Conecte o app ao seu projeto Supabase. A mesma configuração pode ser usada no Windows e Android.",
                                text_align=ft.TextAlign.CENTER,
                                color=self.muted_color(),
                            ),
                            url, key,
                            ft.Button("Salvar e conectar", icon=ft.Icons.CLOUD_DONE, on_click=save),
                            ft.Text("Use somente a chave pública/anon. Nunca coloque a service_role no aplicativo.", size=11, color=self.muted_color()),
                        ],
                    ),
                ),
            ),
        )


    def auth_screen(self):
        password_help=getattr(self.cloud,"password_requirements",lambda:"Use pelo menos 6 caracteres e evite reutilizar senhas.")()
        password_min=getattr(self.cloud,"password_min_length",lambda:6)()
        email = ft.TextField(
            label="E-mail",
            width=420,
            keyboard_type=ft.KeyboardType.EMAIL,
            autofill_hints=[ft.AutofillHint.EMAIL],
        )
        password = ft.TextField(
            label="Senha",
            password=True,
            can_reveal_password=True,
            width=420,
            autofill_hints=[ft.AutofillHint.PASSWORD],
        )
        confirm_password = ft.TextField(
            label="Confirmar senha",
            password=True,
            can_reveal_password=True,
            width=420,
            visible=False,
            autofill_hints=[ft.AutofillHint.PASSWORD],
        )
        mode = {"value": "login"}

        helper = ft.Text(
            "Entre com sua conta para continuar de onde parou.",
            size=11,
            color=self.muted_color(),
            text_align=ft.TextAlign.CENTER,
        )
        offline_note = ft.Text(
            "Primeiro acesso: precisa de internet para criar/validar a conta e carregar o espaço. Depois, somente os dados já sincronizados neste aparelho ficam disponíveis offline.",
            width=420,
            size=10,
            color=self.muted_color(),
            text_align=ft.TextAlign.CENTER,
        )

        status = ft.Text(
            "",
            width=420,
            selectable=True,
            text_align=ft.TextAlign.CENTER,
            visible=False,
            data="auth-status",
        )

        submit_button = ft.Button(
            content="Entrar",
            icon=ft.Icons.LOGIN,
            data="auth-submit",
        )
        requirements = ft.Container(
            visible=False,
            width=420,
            padding=10,
            border_radius=12,
            bgcolor=self.surface_alt_color(),
            content=ft.Text(
                "Senha: " + password_help,
                size=11,
                color=self.muted_color(),
            ),
        )
        active_bg = "#4658C9"
        inactive_bg = self.surface_alt_color()
        login_tab = ft.Button(
            "Entrar", icon=ft.Icons.LOGIN, width=160, elevation=0,
            bgcolor=active_bg, color=ft.Colors.WHITE, data="auth-mode-login",
        )
        signup_tab = ft.Button(
            "Criar conta", icon=ft.Icons.PERSON_ADD_OUTLINED, width=160, elevation=0,
            bgcolor=inactive_bg, color=self.muted_color(), data="auth-mode-signup",
        )
        selected_mode = ft.Text(
            "Você está entrando em uma conta existente.",
            size=11,
            color=self.muted_color(),
            text_align=ft.TextAlign.CENTER,
            data="auth-selected-mode",
        )

        def set_mode(value):
            mode["value"] = value
            creating = value == "signup"
            confirm_password.visible = creating
            requirements.visible = creating
            selected_mode.value = (
                "Você está criando uma conta nova."
                if creating else
                "Você está entrando em uma conta existente."
            )
            helper.value = (
                "Crie sua conta. Depois, confirme o endereço pelo e-mail recebido."
                if creating else
                "Entre com sua conta para continuar de onde parou."
            )
            submit_button.content = "Criar conta" if creating else "Entrar"
            submit_button.icon = ft.Icons.PERSON_ADD if creating else ft.Icons.LOGIN
            login_tab.bgcolor = inactive_bg if creating else active_bg
            login_tab.color = self.muted_color() if creating else ft.Colors.WHITE
            signup_tab.bgcolor = active_bg if creating else inactive_bg
            signup_tab.color = ft.Colors.WHITE if creating else self.muted_color()
            status.visible = False
            self.page.update()

        login_tab.on_click = lambda e: set_mode("login")
        signup_tab.on_click = lambda e: set_mode("signup")

        def show_status(text, error=False):
            status.value = text
            status.color = ft.Colors.RED_700 if error else ft.Colors.GREEN_700
            status.visible = True
            submit_button.disabled = False
            self.page.update()

        async def submit(e):
            status.visible = False
            submit_button.disabled = True
            self.page.update()

            try:
                if not email.value.strip():
                    show_status("Informe seu e-mail.", True)
                    return

                if not password.value:
                    show_status("Informe sua senha.", True)
                    return

                if mode["value"] == "login":
                    result = await asyncio.to_thread(
                        self.cloud.sign_in, email.value, password.value
                    )

                    if not result.user:
                        show_status("O Supabase não retornou um usuário para esse login.", True)
                        return

                    # O sign_in já carrega o contexto. Não chama render_entry aqui,
                    # evitando uma segunda consulta de sessão que antes podia mascarar
                    # o login e voltar silenciosamente para esta tela.
                    if self.cloud.household:
                        self.start_app()
                    else:
                        self.page.clean()
                        self.page.add(self.workspace_screen())
                        self.page.update()
                    return

                if len(password.value) < password_min:
                    show_status(password_help, True)
                    return
                if password.value != confirm_password.value:
                    show_status("As senhas não coincidem.", True)
                    return

                profile_label = email.value.split("@", 1)[0].strip() or "Usuário"
                result = await asyncio.to_thread(
                    self.cloud.sign_up,
                    email.value,
                    password.value,
                    profile_label,
                )

                if result.session and result.user:
                    self.cloud.user = result.user
                    try:
                        self.cloud.load_context()
                    except Exception:
                        # Conta acabou de ser criada; mesmo sem profile/context,
                        # podemos seguir para o onboarding financeiro.
                        self.cloud.household = None
                        self.cloud.member = None

                    self.page.clean()
                    self.page.add(self.workspace_screen())
                    self.page.update()
                else:
                    set_mode("login")
                    show_status(
                        "Conta criada. Confirme o e-mail e volte ao NexGrana para entrar. "
                        "Se o navegador mostrar localhost, a URL de confirmação do Supabase ainda precisa ser configurada."
                    )

            except Exception as ex:
                logger.warning("auth_submit_failed kind=%s mode=%s", type(ex).__name__, mode["value"])
                message = str(ex)
                low = message.lower()

                if "email not confirmed" in low:
                    message = (
                        "Seu e-mail ainda não foi confirmado. "
                        "Abra a mensagem do Supabase no seu e-mail, confirme a conta e tente novamente."
                    )
                elif "invalid login credentials" in low:
                    message = "E-mail ou senha incorretos."
                elif "user already registered" in low or "already registered" in low:
                    message = "Esse e-mail já possui uma conta. Selecione Entrar."
                elif "password" in low and "6" in low:
                    message = "A senha precisa atender aos requisitos mínimos do Supabase."
                elif isinstance(ex, (TransportError, ConnectionError, TimeoutError)) or any(
                    term in low for term in ("connection", "connect", "network", "timeout", "temporary failure")
                ):
                    message = (
                        "Sem conexão com o serviço de autenticação. O primeiro acesso precisa de internet para validar a conta e carregar o espaço. "
                        "Depois, dados já sincronizados neste aparelho podem ser usados offline."
                    )
                elif "rate limit" in low or "too many requests" in low:
                    message = "Muitas tentativas em pouco tempo. Aguarde alguns minutos e tente novamente."
                elif "invalid" in low and "email" in low:
                    message = "Confira se o endereço de e-mail foi digitado corretamente."
                else:
                    message = "O serviço de autenticação não respondeu como esperado. Tente novamente em instantes."

                show_status(f"Não foi possível continuar: {message}", True)

        async def resend(e):
            if not email.value.strip():
                show_status("Informe o e-mail da conta.", True)
                return
            try:
                await asyncio.to_thread(self.cloud.resend_signup_confirmation, email.value)
                show_status("E-mail de confirmação reenviado. Confira também spam e promoções.")
            except Exception:
                show_status("Não foi possível reenviar agora. Aguarde um pouco e tente novamente.", True)

        async def recover(e):
            if not email.value.strip():
                show_status("Informe seu e-mail para recuperar a senha.", True)
                return
            try:
                await asyncio.to_thread(self.cloud.request_password_reset, email.value)
                show_status("Se a conta existir, enviaremos as instruções de recuperação.")
            except Exception:
                show_status("Não foi possível solicitar a recuperação agora.", True)

        submit_button.on_click = submit

        return ft.SafeArea(
            expand=True,
            content=ft.Container(
                alignment=ft.Alignment.CENTER,
                padding=20,
                content=ft.Container(
                    width=500,
                    padding=28,
                    bgcolor=self.surface_color(),
                    border_radius=24,
                    border=ft.Border.all(1, self.border_color()),
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=12,
                        controls=[
                            ft.Icon(
                                ft.Icons.ACCOUNT_BALANCE_WALLET,
                                size=54,
                                color=ft.Colors.INDIGO,
                            ),
                            ft.Text(
                                "NexGrana",
                                size=30,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Text(
                                "Sua conta financeira em qualquer dispositivo.",
                                color=self.muted_color(),
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Row(
                                width=420,
                                alignment=ft.MainAxisAlignment.CENTER,
                                controls=[login_tab, signup_tab],
                            ),
                            selected_mode,
                            email,
                            password,
                            confirm_password,
                            requirements,
                            helper,
                            offline_note,
                            status,
                            submit_button,
                            ft.Row(
                                wrap=True,
                                alignment=ft.MainAxisAlignment.CENTER,
                                controls=[
                                    ft.TextButton("Reenviar confirmação", on_click=resend),
                                    ft.TextButton("Esqueci minha senha", on_click=recover),
                                ],
                            ),
                        ],
                    ),
                ),
            ),
        )


    def workspace_screen(self):
        action = {"value": "create"}
        create_tab = ft.Button("Criar meu espaço", icon=ft.Icons.ADD_HOME_OUTLINED, disabled=True)
        join_tab = ft.OutlinedButton("Entrar em uma família", icon=ft.Icons.GROUP_ADD_OUTLINED)
        kind = ft.RadioGroup(
            value="Individual",
            content=ft.Row(
                controls=[
                    ft.Radio(value="Individual", label="Individual"),
                    ft.Radio(value="Família/Casal", label="Família/Casal"),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
            ),
        )
        kind_box = ft.Container(
            width=500,
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            border=ft.Border.all(1, self.subtle_color()),
            border_radius=8,
            content=ft.Column(
                spacing=4,
                controls=[
                    ft.Text("Tipo de controle", size=12, color=ft.Colors.GREY_700),
                    kind,
                ],
            ),
        )
        household_name = ft.TextField(label="Nome da conta", width=500, value="Meu NexGrana")
        default_name = ((self.cloud.profile or {}).get("full_name") or "")
        owner_name = ft.TextField(
            label="Seu nome no NexGrana",
            width=500,
            value=default_name,
        )
        join_name = ft.TextField(
            label="Seu nome no NexGrana",
            width=500,
            value=default_name,
        )
        family_code = ft.TextField(
            label="Código da família",
            hint_text="Ex.: ABC12345",
            width=500,
        )

        member_fields = []
        members_column = ft.Column(spacing=10)
        members_title = ft.Text("Integrantes", size=18, weight=ft.FontWeight.BOLD)
        members_help = ft.Text(
            "Família/Casal precisa ter de 2 a 7 pessoas. Você já é o primeiro integrante.",
            size=11,
            color=self.muted_color(),
        )
        add_member_button = ft.OutlinedButton("Adicionar integrante", icon=ft.Icons.PERSON_ADD)
        create_section = ft.Column(spacing=12)
        join_section = ft.Column(spacing=12)
        status = ft.Text("", width=500, selectable=True, text_align=ft.TextAlign.CENTER, visible=False)
        continue_button = ft.Button("Continuar", icon=ft.Icons.ARROW_FORWARD)

        def show_status(text, error=False):
            status.value = text
            status.color = ft.Colors.RED_700 if error else ft.Colors.GREEN_700
            status.visible = True
            continue_button.disabled = False
            self.page.update()

        def remove_member(e):
            field = e.control.data
            if field in member_fields and len(member_fields) > 1:
                member_fields.remove(field)
                rebuild_members()
                self.page.update()

        def rebuild_members():
            members_column.controls.clear()
            for i, field in enumerate(member_fields, start=2):
                field.label = f"Nome do integrante {i}"
                controls = [ft.Container(expand=True, content=field)]
                if len(member_fields) > 1:
                    controls.append(
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            tooltip="Remover integrante",
                            data=field,
                            on_click=remove_member,
                        )
                    )
                members_column.controls.append(ft.Row(controls=controls))
            add_member_button.disabled = len(member_fields) >= 6

        def add_member(e=None):
            if len(member_fields) >= 6:
                return
            member_fields.append(ft.TextField(width=440))
            rebuild_members()
            if e:
                self.page.update()

        add_member_button.on_click = add_member

        def sync_sections(e=None):
            creating = action["value"] == "create"
            create_section.visible = creating
            join_section.visible = not creating

            family_mode = kind.value == "Família/Casal"
            members_title.visible = family_mode
            members_help.visible = family_mode
            members_column.visible = family_mode
            add_member_button.visible = family_mode
            self.page.update()

        kind.on_change = sync_sections

        def choose_action(value):
            action["value"] = value
            creating = value == "create"
            create_tab.disabled = creating
            join_tab.disabled = not creating
            if creating and not owner_name.value.strip():
                owner_name.value = join_name.value
            if not creating and not join_name.value.strip():
                join_name.value = owner_name.value
            status.visible = False
            sync_sections()

        create_tab.on_click = lambda e: choose_action("create")
        join_tab.on_click = lambda e: choose_action("join")

        async def submit(e):
            status.visible = False
            continue_button.disabled = True
            self.page.update()
            try:
                if action["value"] == "join":
                    if not family_code.value.strip():
                        show_status("Informe o código da família.", True)
                        return
                    await asyncio.to_thread(
                        self.cloud.join_family,
                        family_code.value.strip(),
                        join_name.value.strip() or default_name or "Usuário",
                    )
                    self.start_app()
                    return

                if not owner_name.value.strip():
                    show_status("Informe seu nome no NexGrana.", True)
                    return
                if not household_name.value.strip():
                    show_status("Informe um nome para sua conta.", True)
                    return

                if kind.value == "Individual":
                    names = [owner_name.value.strip()]
                else:
                    names = [owner_name.value.strip()]
                    names += [f.value.strip() for f in member_fields if f.value and f.value.strip()]
                    if len(names) < 2:
                        show_status("Informe pelo menos mais uma pessoa para Família/Casal.", True)
                        return
                    if len(names) > 7:
                        show_status("A família pode ter no máximo 7 integrantes.", True)
                        return
                    normalized = [n.casefold() for n in names]
                    if len(normalized) != len(set(normalized)):
                        show_status("Os integrantes precisam ter nomes diferentes.", True)
                        return

                await asyncio.to_thread(
                    self.cloud.create_workspace,
                    "Individual" if kind.value == "Individual" else "Família",
                    household_name.value.strip(),
                    owner_name.value.strip(),
                    member_names=names,
                )
                self.start_app()
            except Exception:
                show_status("Não foi possível criar o espaço. O primeiro acesso e a criação do espaço precisam de internet; conecte-se e tente novamente.", True)

        continue_button.on_click = submit

        create_section.controls = [
            ft.Text("Criar meu espaço", size=20, weight=ft.FontWeight.BOLD),
            kind_box,
            household_name,
            owner_name,
            members_title,
            members_help,
            members_column,
            add_member_button,
        ]
        join_section.controls = [
            ft.Text("Entrar em uma família", size=20, weight=ft.FontWeight.BOLD),
            join_name,
            family_code,
            ft.Text("Peça o código ao administrador da família.", size=11, color=self.muted_color()),
        ]

        add_member()  # usuário + este campo = mínimo de 2 no modo família
        members_title.visible = False
        members_help.visible = False
        members_column.visible = False
        add_member_button.visible = False
        join_section.visible = False

        return ft.SafeArea(
            expand=True,
            content=ft.Container(
                alignment=ft.Alignment.CENTER,
                padding=20,
                content=ft.Container(
                    width=600,
                    padding=28,
                    bgcolor=self.surface_color(),
                    border_radius=24,
                    border=ft.Border.all(1, self.border_color()),
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=14,
                        scroll=ft.ScrollMode.AUTO,
                        controls=[
                            ft.Text("Configure seu NexGrana", size=28, weight=ft.FontWeight.BOLD),
                            ft.Text(
                                "Use sozinho ou compartilhe o controle com sua família.",
                                color=self.muted_color(),
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Text("Como você quer começar?", size=12, color=self.muted_color()),
                            ft.Row(
                                width=500,
                                wrap=True,
                                alignment=ft.MainAxisAlignment.CENTER,
                                controls=[create_tab, join_tab],
                            ),
                            create_section,
                            join_section,
                            status,
                            continue_button,
                        ],
                    ),
                ),
            ),
        )
