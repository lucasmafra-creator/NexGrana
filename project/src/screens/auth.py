from ui.common import ft, load_config, save_config

class AuthScreen:
    def render_entry(self):
        self.page.clean()

        if not self.cloud.configured():
            self.page.add(self.setup_cloud_screen())
            return

        try:
            self.cloud.connect()
        except Exception as ex:
            self.page.add(
                self.error_screen(
                    "Não foi possível conectar ao Supabase",
                    str(ex),
                )
            )
            return

        try:
            user = self.cloud.current_user()
        except Exception:
            # Sem sessão válida: mostra login.
            user = None

        if not user:
            self.page.add(self.auth_screen())
            return

        # Usuário autenticado. O contexto financeiro é carregado separadamente
        # para não mascarar um login válido.
        try:
            self.cloud.load_context()
        except Exception as ex:
            self.page.add(
                self.error_screen(
                    "Login realizado, mas houve erro ao carregar sua conta",
                    str(ex),
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
            except Exception as ex:
                self.snack(f"Não foi possível conectar: {ex}", True)

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
                            ft.Text("NexGrana 0.19.0", size=28, weight=ft.FontWeight.BOLD),
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
        email = ft.TextField(label="E-mail", width=420)
        password = ft.TextField(
            label="Senha",
            password=True,
            can_reveal_password=True,
            width=420,
        )
        mode = ft.Dropdown(
            label="O que deseja fazer?",
            value="Entrar",
            width=420,
            options=[
                ft.DropdownOption("Entrar"),
                ft.DropdownOption("Criar conta"),
            ],
        )

        helper = ft.Text(
            "Entre com sua conta ou crie uma nova usando apenas e-mail e senha.",
            size=11,
            color=self.muted_color(),
            text_align=ft.TextAlign.CENTER,
        )

        status = ft.Text(
            "",
            width=420,
            selectable=True,
            text_align=ft.TextAlign.CENTER,
            visible=False,
        )

        submit_button = ft.Button(
            "Continuar",
            icon=ft.Icons.LOGIN,
        )

        def show_status(text, error=False):
            status.value = text
            status.color = ft.Colors.RED_700 if error else ft.Colors.GREEN_700
            status.visible = True
            submit_button.disabled = False
            self.page.update()

        def submit(e):
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

                if mode.value == "Entrar":
                    result = self.cloud.sign_in(email.value, password.value)

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

                profile_label = email.value.split("@", 1)[0].strip() or "Usuário"
                result = self.cloud.sign_up(
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
                    mode.value = "Entrar"
                    show_status(
                        "Conta criada. Confirme o e-mail enviado pelo Supabase e depois entre com a mesma senha."
                    )

            except Exception as ex:
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

                show_status(f"Não foi possível continuar: {message}", True)

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
                            mode,
                            email,
                            password,
                            helper,
                            status,
                            submit_button,
                        ],
                    ),
                ),
            ),
        )


    def workspace_screen(self):
        action = ft.Dropdown(
            label="O que deseja fazer?",
            value="Criar meu espaço",
            width=500,
            options=[
                ft.DropdownOption("Criar meu espaço"),
                ft.DropdownOption("Entrar em uma família"),
            ],
        )
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
        owner_name = ft.TextField(
            label="Seu nome no NexGrana",
            width=500,
            value=((self.cloud.profile or {}).get("full_name") or ""),
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
            creating = action.value == "Criar meu espaço"
            create_section.visible = creating
            join_section.visible = not creating

            family_mode = kind.value == "Família/Casal"
            members_title.visible = family_mode
            members_help.visible = family_mode
            members_column.visible = family_mode
            add_member_button.visible = family_mode
            self.page.update()

        action.on_change = sync_sections
        kind.on_change = sync_sections

        def submit(e):
            status.visible = False
            continue_button.disabled = True
            self.page.update()
            try:
                if action.value == "Entrar em uma família":
                    if not family_code.value.strip():
                        show_status("Informe o código da família.", True)
                        return
                    self.cloud.join_family(
                        family_code.value.strip(),
                        owner_name.value.strip() or ((self.cloud.profile or {}).get("full_name") or "Usuário"),
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

                self.cloud.create_workspace(
                    "Individual" if kind.value == "Individual" else "Família",
                    household_name.value.strip(),
                    owner_name.value.strip(),
                    member_names=names,
                )
                self.start_app()
            except Exception as ex:
                show_status(f"Não foi possível continuar: {ex}", True)

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
            owner_name,
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
                            action,
                            create_section,
                            join_section,
                            status,
                            continue_button,
                        ],
                    ),
                ),
            ),
        )


