from ui.common import AFFILIATE_DISCLOSURE, POLICY_TEXT, asyncio, brl, defaultdict, export_snapshot, ft, logger, money, storage_dir, uuid, write_backup
from build_config import BUILD_CHANNEL, QA_ACCOUNT_HINT
from ui.theme import VISUAL_STYLES
from services.qa_diagnostics import qa_failure

class SettingsScreen:
    def nex_skin_dialog(self, e=None):
        from services.nex_skins import SKINS, SKIN_META, allowed_auto_skins, occasion_skin, preview_asset
        current=self.preferences.get("nex_skin", "auto")
        allowed=allowed_auto_skins(self.preferences)
        context_switch=ft.Switch(label="Permitir alternância automática por contexto",value=bool(self.preferences.get("nex_context_auto",False)))
        allow_checks=[]
        def choose(key):
            self.preferences["nex_skin"]=key
            self.save_preferences()
            self.page.pop_dialog()
            self.render()
            self.snack("Visual do Nex atualizado.")
        cards=[]
        for key,(label,asset) in SKINS.items():
            metadata=SKIN_META.get(key,{})
            selected_asset=preview_asset(key)
            is_selected=current==key
            cards.append(ft.Container(
                col={"xs":6,"sm":4,"md":3,"lg":2},padding=8,border_radius=14,
                bgcolor=self.surface_alt_color(),
                border=ft.Border.all(2 if is_selected else 1,self.visual_style()["accent"] if is_selected else self.border_color()),
                on_click=lambda e,k=key:choose(k),
                content=ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER,spacing=6,controls=[
                    ft.Image(src=selected_asset,width=112,height=118,fit=ft.BoxFit.CONTAIN,gapless_playback=True),
                    ft.Text(label,size=11,weight=ft.FontWeight.BOLD,text_align=ft.TextAlign.CENTER,max_lines=2),
                    ft.Text(metadata.get("category", "Estilo"),size=9,color=self.muted_color(),text_align=ft.TextAlign.CENTER,max_lines=2),
                    ft.Text(metadata.get("when") or "Escolha manual",size=8,color=self.muted_color(),text_align=ft.TextAlign.CENTER,max_lines=2),
                ]),
            ))
            if key!="auto":
                allow_checks.append((key,ft.Checkbox(label=label,value=key in allowed)))
        def save_auto_preferences(_):
            self.preferences["nex_context_auto"]=bool(context_switch.value)
            self.preferences["nex_auto_allowed_skins"]=[key for key,control in allow_checks if control.value]
            self.save_preferences()
            self.page.pop_dialog()
            self.snack("A alternância automática do Nex foi atualizada.")
            self.render()
        active=occasion_skin()
        auto_state=(f"Hoje: {SKINS[active][0]} está disponível só se autorizada abaixo." if active else "Hoje, o automático usa o Nex original.")
        width,height=self.dialog_dimensions(900,760)
        self.page.show_dialog(ft.AlertDialog(
            title=ft.Text("Visual e skins do Nex"),
            content=ft.Column(width=width,height=height,scroll=ft.ScrollMode.AUTO,controls=[
                ft.Text("Escolha uma aparência manual ou selecione Automático. No modo automático, datas especiais e troca por contexto só usam artes liberadas por você abaixo. A escolha manual mantém a mesma aparência em todas as telas.",size=11),
                ft.Text(auto_state,size=10,color=self.muted_color()),
                ft.Divider(),
                ft.Text("Aparências permitidas no modo automático",size=13,weight=ft.FontWeight.BOLD),
                context_switch,
                ft.Text("A troca por contexto funciona apenas quando Automático estiver selecionado. Se nenhum visual autorizado corresponder à tela, o Nex original permanece.",size=10,color=self.muted_color()),
                ft.ResponsiveRow(spacing=2,run_spacing=2,controls=[ft.Container(col={"xs":6,"sm":4,"md":3},content=control) for _,control in allow_checks]),
                ft.Divider(),
                ft.Text("Escolha manual",size=13,weight=ft.FontWeight.BOLD),
                ft.ResponsiveRow(spacing=7,run_spacing=7,controls=cards),
            ]),actions=[ft.TextButton("Salvar automações",on_click=save_auto_preferences),ft.TextButton("Fechar",on_click=lambda e:self.page.pop_dialog())],
        ))

    def appearance_previews(self):
        """Small live palette samples for the account-scoped visual choices."""
        selected=self.preferences.get("visual_style", "original")
        cards=[]
        for key,style in VISUAL_STYLES.items():
            cards.append(ft.Container(
                col={"xs":12,"sm":4},padding=10,border_radius=14,
                bgcolor=self.surface_alt_color(),
                border=ft.Border.all(2 if key==selected else 1,style["accent"] if key==selected else style["border"]),
                on_click=lambda e,choice=key:self.choose_visual_style(choice),
                content=ft.Column(spacing=7,controls=[
                    ft.Row(spacing=5,controls=[
                        ft.Container(width=16,height=16,border_radius=5,bgcolor=style["background"]),
                        ft.Container(width=16,height=16,border_radius=5,bgcolor=style["surface_alt"]),
                        ft.Container(width=16,height=16,border_radius=5,bgcolor=style["accent"]),
                    ]),
                    ft.Text(style["label"],size=11,weight=ft.FontWeight.BOLD),
                ]),
            ))
        return ft.ResponsiveRow(spacing=8,run_spacing=8,controls=cards)

    def nex_vivo_dialog(self, e=None):
        from nex_controller import NexSettings
        current=NexSettings.from_mapping(self.preferences.get("nex_vivo"))
        enabled=ft.Switch(label="Nex Vivo",value=current.enabled)
        intensity=ft.Dropdown(
            label="Intensidade",value=current.intensity,
            options=[
                ft.DropdownOption(key="discreet",text="Discreto — só eventos importantes"),
                ft.DropdownOption(key="normal",text="Normal — equilíbrio entre foco e personalidade"),
                ft.DropdownOption(key="animated",text="Animado — experiência completa"),
            ],
        )
        animations=ft.Switch(label="Microanimações",value=current.animations)
        effects=ft.Switch(label="Efeitos especiais",value=current.effects)
        reduced=ft.Switch(label="Reduzir movimento",value=current.reduced_motion)

        def save(_):
            values=NexSettings.from_mapping({
                "enabled":enabled.value,"intensity":intensity.value,
                "animations":animations.value,"effects":effects.value,
                "sound":False,"reduced_motion":reduced.value,
            }).public_payload()
            self.preferences["nex_vivo"]=values
            self.save_preferences()
            self.nex_state.configure(values)
            self.page.pop_dialog()
            self.snack("Preferências do Nex Vivo atualizadas.")
            self.render()

        width,height=self.dialog_dimensions(540,620)
        self.page.show_dialog(ft.AlertDialog(
            title=ft.Text("Nex Vivo"),
            content=ft.Column(width=width,height=height,scroll=ft.ScrollMode.AUTO,spacing=10,controls=[
                ft.Text("O Nex reage a eventos já concluídos, mas nunca altera saldo, renda, despesas ou metas.",size=11,color=self.muted_color()),
                enabled,intensity,animations,effects,reduced,
                ft.Container(padding=12,border_radius=12,bgcolor=self.surface_alt_color(),content=ft.Text(
                    "Qualidade primeiro: se uma animação futura falhar, o Nex volta automaticamente à imagem HD aprovada.",size=10
                )),
            ]),
            actions=[
                ft.TextButton("Cancelar",on_click=lambda _:self.page.pop_dialog()),
                ft.Button("Salvar",on_click=save),
            ],
        ))

    def nex_preferences_dialog(self, e=None):
        current=self.nex_preferences()
        name=ft.TextField(
            label="Como prefere ser chamado? (opcional)",
            value=current.get("preferred_name") or "",
            hint_text="Ex.: Mafra, Lucas ou sem apelido",
            max_length=32,
        )
        tone=ft.Dropdown(
            label="Tom da conversa",value=current.get("tone") or "friendly",
            options=[ft.DropdownOption(key="friendly",text="Descontraído"),ft.DropdownOption(key="neutral",text="Neutro")],
        )
        detail=ft.Dropdown(
            label="Tamanho das explicações",value=current.get("detail") or "balanced",
            options=[
                ft.DropdownOption(key="short",text="Curtas"),
                ft.DropdownOption(key="balanced",text="Equilibradas"),
                ft.DropdownOption(key="detailed",text="Detalhadas"),
            ],
        )
        remember=ft.Switch(label="Lembrar nas próximas conversas",value=bool(current.get("remember")))

        def save(_):
            from services.nex_conversation import AssistantPreferences
            values=AssistantPreferences.from_mapping({
                "preferred_name":name.value,"tone":tone.value,"detail":detail.value,"remember":remember.value,
            }).public_payload()
            self._nex_session_preferences=values
            if values["remember"]:
                self.preferences["nex_preferences"]=values
                self.save_preferences()
            else:
                self.preferences.pop("nex_preferences",None)
                self.save_preferences()
            self.page.pop_dialog()
            self.snack("Preferências do Nex atualizadas.")

        def forget(_):
            self.forget_nex_preferred_name()
            self._nex_session_preferences={}
            self.preferences.pop("nex_preferences",None)
            self.save_preferences()
            self.page.pop_dialog()
            self.snack("Preferências lembradas pelo Nex foram removidas.")

        width,height=self.dialog_dimensions(520,560)
        self.page.show_dialog(ft.AlertDialog(
            title=ft.Text("Personalizar conversa com o Nex"),
            content=ft.Column(width=width,height=height,scroll=ft.ScrollMode.AUTO,controls=[
                ft.Text("Isso muda apenas a conversa. Não altera seu nome de cadastro nem o perfil financeiro selecionado.",size=11,color=self.muted_color()),
                name,tone,detail,remember,
                ft.Container(padding=12,border_radius=12,bgcolor=self.surface_alt_color(),content=ft.Text(
                    f"Prévia: Oi{', '+(current.get('preferred_name') or 'por aí') if current.get('preferred_name') else ''}! Vou adaptar o tom e o nível de detalhe sem inventar dados.",size=11
                )),
            ]),
            actions=[
                ft.TextButton("Esquecer preferências",on_click=forget),
                ft.TextButton("Cancelar",on_click=lambda _:self.page.pop_dialog()),
                ft.Button("Salvar",on_click=save),
            ],
        ))

    def show_tutorial_offer(self, force=False):
        if self._tutorial_offer_shown and not force:
            return
        if self.preferences.get("tutorial_offer_choice") in {"accepted","explore"} and not force:
            return
        self._tutorial_offer_shown = True

        def explore(e):
            self.preferences["tutorial_offer_choice"] = "explore"
            self.save_preferences()
            self.page.pop_dialog()

        def later(e):
            self.preferences["tutorial_offer_choice"] = "remember"
            self.save_preferences()
            self.page.pop_dialog()

        def start(e):
            self.preferences["tutorial_offer_choice"] = "accepted"
            self.save_preferences()
            self.page.pop_dialog()
            self._go_tutorial("welcome")

        dialog = ft.AlertDialog(
            modal=False,
            title=ft.Text("Quer uma ajuda para começar?"),
            content=ft.Column(tight=True,controls=[
                ft.Image(src=self.nex_asset("study","card"),width=104,height=104,fit=ft.BoxFit.CONTAIN),
                ft.Text("Aprenda cadastrando exemplos em um espaço de treino isolado. Você decide quando algo pode virar um registro real.",color=self.muted_color()),
            ]),
            actions=[
                ft.TextButton("Explorar sozinho", on_click=explore),
                ft.TextButton("Lembrar depois", on_click=later),
                ft.Button("Começar agora", icon=ft.Icons.PLAY_ARROW, on_click=start),
            ],
        )
        self.page.show_dialog(dialog)

    def tutorial_dialog(self, start=0):
        # Compatibility entrypoint; all onboarding uses the 13 interactive steps.
        self._go_tutorial("welcome")

    def qa_reset_dialog(self, e=None):
        confirmation=ft.TextField(label='Digite RESETAR_TESTE',autocorrect=False)
        enroll_confirmation=ft.TextField(label='Para vincular, digite VINCULAR_TESTE',autocorrect=False)
        status=ft.Text('',visible=False,color=ft.Colors.RED_300)
        reset_button=ft.Button('Reiniciar ambiente de teste',icon=ft.Icons.RESTART_ALT)
        enroll_button=ft.OutlinedButton('Vincular este espaço como teste')
        dialog=ft.AlertDialog(
            title=ft.Text('Reiniciar homologação'),
            content=ft.Column(tight=True,scroll=ft.ScrollMode.AUTO,controls=[
                ft.Text('Esta ação volta à escolha “Criar meu espaço / Entrar em uma família”. A conta e a senha permanecem.'),
                ft.Text('Se você entrou em uma família, somente sua participação é removida. Se o espaço é seu e há outros integrantes, transfira a propriedade antes; o reset será bloqueado para proteger os dados deles.',size=10,color=self.muted_color()),
                ft.Text('Se este espaço individual é antigo, vincule-o uma vez como ambiente de teste. Apenas o testador QA autorizado e único dono pode fazer isso. Depois, o reset poderá excluir os registros deste espaço.',size=10,color=self.muted_color()),
                enroll_confirmation,enroll_button,confirmation,status,
            ]),
            actions=[ft.TextButton('Cancelar',on_click=lambda e:self.page.pop_dialog()),reset_button],
        )
        async def reset(e):
            if confirmation.value!='RESETAR_TESTE':
                status.value='Digite exatamente RESETAR_TESTE.'
                status.visible=True
                self.page.update()
                return
            reset_button.disabled=True;self.page.update()
            try:
                await asyncio.to_thread(self.cloud.reset_qa_workspace,confirmation.value)
                self.page.pop_dialog()
                self.root_host=self.root_safe_area=None
                self._members_cache=[]
                self.page.navigation_bar=None
                self.page.clean();self.page.add(self.workspace_screen());self.page.update()
            except Exception as exc:
                status.value=qa_failure(exc);status.visible=True
                reset_button.disabled=False;self.page.update()
        reset_button.on_click=reset
        async def enroll(_):
            if enroll_confirmation.value!='VINCULAR_TESTE':
                status.value='Digite exatamente VINCULAR_TESTE para vincular o espaço.';status.visible=True;self.page.update();return
            enroll_button.disabled=True;self.page.update()
            try:
                await asyncio.to_thread(self.cloud.enroll_owned_qa_workspace,enroll_confirmation.value)
                status.value='Espaço vinculado. Agora você pode digitar RESETAR_TESTE.'
                status.color=ft.Colors.GREEN_300
            except Exception as exc:
                status.value=qa_failure(exc)
            status.visible=True;enroll_button.disabled=False;self.page.update()
        enroll_button.on_click=enroll
        self.page.show_dialog(dialog)

    async def export_backup_db(self, e=None):
        try:
            payload=await asyncio.to_thread(export_snapshot,self.cloud)
            temp=storage_dir()/('export-'+uuid.uuid4().hex+'.db')
            await asyncio.to_thread(write_backup,temp,payload)
            try:
                picker=ft.FilePicker()
                self.page.services.append(picker)
                await picker.save_file(dialog_title="Salvar exportação dos seus dados",file_name="nexgrana-export.db",src_bytes=temp.read_bytes())
            finally:
                temp.unlink(missing_ok=True)
        except Exception as exc:
            self.snack("Não foi possível exportar todos os dados. Tente novamente após sincronizar.",True)
            logger.warning("export_failed kind=%s",type(exc).__name__)

    def delete_account_dialog(self, e=None):
        mode=(self.cloud.household or {}).get('mode')
        if mode!='individual':
            self.snack('Este espaço é compartilhado. A exclusão automática não pode apagar dados de outras pessoas. Procure o responsável pelo espaço.',True)
            return
        confirmation=ft.TextField(label='Digite EXCLUIR MINHA CONTA',autofocus=True)
        status=ft.Text('',visible=False,color=ft.Colors.RED_300)
        button=ft.Button('Excluir minha conta e espaço',icon=ft.Icons.DELETE_FOREVER)
        async def execute(_):
            if confirmation.value!='EXCLUIR MINHA CONTA':
                status.value='Digite a frase completa para confirmar.';status.visible=True;self.page.update();return
            button.disabled=True;self.page.update()
            try:
                await asyncio.to_thread(self.cloud.delete_my_individual_account,confirmation.value)
                self.page.pop_dialog()
                self._members_cache=[]
                self.page.navigation_bar=None
                self.render_entry()
            except Exception as exc:
                logger.warning('account_deletion_failed kind=%s',type(exc).__name__)
                status.value='Exclusão não concluída. Verifique a conexão e a migração 0.24.5; se a conta possui outros espaços, use o atendimento.'
                status.visible=True;button.disabled=False;self.page.update()
        button.on_click=execute
        self.page.show_dialog(ft.AlertDialog(
            title=ft.Text('Excluir conta e dados'),
            content=ft.Column(width=420,height=230,scroll=ft.ScrollMode.AUTO,controls=[
                ft.Text('Esta ação apaga permanentemente sua conta e todo o espaço individual na nuvem. Exporte antes se quiser guardar uma cópia.'),
                ft.Text('A ação exige internet e não pode ser desfeita.',weight=ft.FontWeight.BOLD),
                confirmation,status,
            ]),actions=[ft.TextButton('Cancelar',on_click=lambda e:self.page.pop_dialog()),button],
        ))


    def wallet_dialog(self, e=None):
        try:
            wallets=self.cloud.list_wallets()
        except Exception:
            self.snack("Execute o patch V2 no Supabase antes de usar Carteira.", True); return
        member=ft.Dropdown(label="Pessoa", options=self.member_options(), width=300)
        if self.current_member(): member.value=str(self.current_member()["id"])
        name=ft.TextField(label="Nome", hint_text="Ex.: Nubank Mafra")
        wtype=ft.Dropdown(label="Tipo", value="Cartão de crédito", options=[
            ft.DropdownOption("Cartão de crédito"),ft.DropdownOption("Conta"),ft.DropdownOption("Carteira")
        ])
        limitv=ft.TextField(label="Limite (opcional)", value="0")
        close=ft.TextField(label="Dia de fechamento", value="0")
        due=ft.TextField(label="Dia de vencimento", value="0")
        list_controls=[]
        for w in wallets:
            person=(w.get("household_members") or {}).get("display_name","—")
            list_controls.append(ft.ListTile(
                leading=ft.Icon(ft.Icons.CREDIT_CARD),
                title=ft.Text(w["name"]),
                subtitle=ft.Text(f"{person} • {w['wallet_type']} • limite {brl(w.get('limit_amount',0))}"),
                trailing=ft.IconButton(ft.Icons.DELETE_OUTLINE,on_click=lambda e,rid=w["id"]: (self.cloud.delete_wallet(rid),self.page.pop_dialog(),self.wallet_dialog()))
            ))
        dialog=ft.AlertDialog(title=ft.Text("Carteira — sem dados sensíveis de cartão"),
            content=ft.Column(width=520,height=520,scroll=ft.ScrollMode.ALWAYS,controls=[
                ft.Text("Não armazene número completo do cartão, CVV, senha ou credenciais bancárias.",size=11,color=ft.Colors.ORANGE_700),
                *list_controls, ft.Divider(), member,name,wtype,limitv,close,due
            ]))
        def save(e):
            try:
                self.cloud.add_wallet(member.value,name.value,wtype.value,money(limitv.value),int(close.value or 0),int(due.value or 0))
                self.page.pop_dialog(); self.wallet_dialog()
            except Exception as ex:self.snack(str(ex),True)
        dialog.actions=[ft.TextButton("Fechar",on_click=lambda e:self.page.pop_dialog()),ft.Button("Adicionar",on_click=save)]
        self.page.show_dialog(dialog)


    def semester_dialog(self, e=None):
        year=int(self.month[3:]); month=int(self.month[:2])
        first_half=month<=6
        months=[f"{m:02d}/{year}" for m in (range(1,7) if first_half else range(7,13))]
        label=f"{'Jan–Jun' if first_half else 'Jul–Dez'}/{year}"
        incomes=[]; expenses=[]
        for mm in months:
            incomes.extend(self.cloud.list_income(mm))
            expenses.extend(self.cloud.list_expenses(mm))
        total_i=sum(float(x["amount"]) for x in incomes)
        total_e=sum(float(x["amount"]) for x in expenses)
        cats=defaultdict(float)
        for x in expenses: cats[x["category"]]+=float(x["amount"])
        summary_text=f"{label}: renda {brl(total_i)}, despesas {brl(total_e)}, saldo {brl(total_i-total_e)}."
        dialog=ft.AlertDialog(title=ft.Text("Fechamento semestral"),content=ft.Column(tight=True,controls=[
            ft.Text(summary_text,weight=ft.FontWeight.BOLD),
            ft.Text("Salve um resumo semestral para comparação. A remoção de lançamentos detalhados permanece desativada porque o saldo do NexGrana é contínuo e depende do histórico.",size=11),
            ft.Text("O resumo fica disponível para comparações futuras do Assistente.",size=11,color=self.muted_color())
        ]))
        def save_summary(e):
            try:
                start=f"{year}-{'01-01' if first_half else '07-01'}"; end=f"{year}-{'06-30' if first_half else '12-31'}"
                self.cloud.save_semester_summary(start,end,total_i,total_e,total_i-total_e,dict(cats))
                self.snack("Resumo semestral salvo na nuvem.")
            except Exception as ex:self.snack(f"Execute o patch V2 no Supabase: {ex}",True)
        dialog.actions=[
            ft.TextButton("Cancelar",on_click=lambda e:self.page.pop_dialog()),
            ft.OutlinedButton("Salvar só o resumo",on_click=save_summary),
            ft.Text("O histórico detalhado é preservado para manter o saldo contínuo.",size=10)
        ]
        self.page.show_dialog(dialog)


    def more_screen(self):
        members = self.members()
        member_controls = []
        for m in members:
            member_controls.append(
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.PERSON),
                    title=ft.Text(m["display_name"]),
                    subtitle=ft.Text("Administrador" if m["role"] == "owner" else "Membro"),
                )
            )

        invite = self.cloud.household.get("invite_code", "—")
        family_info = (
            ft.Container(
                padding=15, bgcolor=self.surface_color(), border_radius=16,
                border=ft.Border.all(1, self.border_color()),
                content=ft.Column(controls=[
                    ft.Text("Família", size=16, weight=ft.FontWeight.BOLD),
                    ft.Text(f"{len(members)}/7 membros"),
                    ft.Text(f"Código para convite: {invite}", weight=ft.FontWeight.BOLD),
                    *member_controls,
                ]),
            )
            if self.cloud.household["mode"] == "family"
            else ft.Container(
                padding=15, bgcolor=self.surface_color(), border_radius=16,
                content=ft.Text("Conta Individual • seus dados ficam vinculados somente a esta conta."),
            )
        )

        qa_card = ft.Container()
        if BUILD_CHANNEL == 'qa':
            qa_card=ft.Container(
                padding=15,bgcolor=self.warning_surface_color(),border_radius=16,
                border=ft.Border.all(1,ft.Colors.AMBER_300),
                content=ft.Column(spacing=6,controls=[
                    ft.Text('Homologação reiniciável',size=16,weight=ft.FontWeight.BOLD),
                    ft.Text(f'Conta sugerida: {QA_ACCOUNT_HINT}. A autorização real é feita pelo UUID no servidor.',size=10,color=self.muted_color()),
                    ft.Button('Reiniciar dados de teste',icon=ft.Icons.RESTART_ALT,on_click=self.qa_reset_dialog),
                ]),
            )

        try:
            sync_summary=self.cloud.sync_summary()
        except Exception:
            sync_summary={"queued":0,"conflict":0,"rejected":0,"total":0}
        if sync_summary["conflict"] or sync_summary["rejected"]:
            sync_detail=(f"{sync_summary['conflict']} conflito(s) e "
                         f"{sync_summary['rejected']} alteração(ões) recusada(s). "
                         "Esses registros não alteram o saldo até a revisão.")
        elif sync_summary["queued"]:
            sync_detail=f"{sync_summary['queued']} alteração(ões) aguardando envio."
        elif getattr(self.cloud,"online",True):
            sync_detail="Tudo sincronizado."
        else:
            sync_detail="Offline com dados locais protegidos."

        async def sync_now(e):
            try:
                await asyncio.to_thread(self.cloud.refresh_core_data)
                self.last_sync="agora"
                self.snack("Sincronização concluída.")
                self.render()
            except Exception:
                self.snack("Não foi possível sincronizar agora. Seus dados locais foram preservados.",True)

        def discard_errors(e):
            rows=self.cloud.discard_sync_errors()
            self.snack(f"{len(rows)} alteração(ões) local(is) descartada(s). Os registros confirmados foram preservados.")
            self.render()

        return ft.Column(
            expand=True, scroll=ft.ScrollMode.ALWAYS,
            controls=[
                self.header("Mais", "Configurações, conta, segurança e dados"),
                ft.Container(
                    padding=16,
                    content=ft.Column(spacing=12, controls=[
                        family_info,
                        qa_card,
                        ft.Container(
                            padding=15, bgcolor=self.surface_color(), border_radius=16,
                            border=ft.Border.all(1, self.border_color()),
                            content=ft.Column(controls=[
                                ft.Text("Sincronização", size=16, weight=ft.FontWeight.BOLD),
                                ft.Text(sync_detail),
                                ft.Text(f"Última atualização: {self.last_sync}"),
                                ft.Row(wrap=True,controls=[
                                    ft.Button("Sincronizar agora",icon=ft.Icons.SYNC,on_click=lambda e:self.page.run_task(sync_now,e)),
                                    ft.TextButton("Tentar recusadas novamente",visible=bool(sync_summary["rejected"]),on_click=lambda e:(self.cloud.retry_rejected_sync(),self.render())),
                                    ft.TextButton("Descartar erros locais",visible=bool(sync_summary["conflict"] or sync_summary["rejected"]),on_click=discard_errors),
                                ]),
                            ]),
                        ),
                        ft.Container(
                            padding=15, bgcolor=self.surface_color(), border_radius=16,
                            border=ft.Border.all(1, self.border_color()),
                            content=ft.Column(controls=[
                                ft.Text("Aparência", size=16, weight=ft.FontWeight.BOLD),
                                ft.Text("Escolha o visual da sua conta. Sua escolha fica separada da família e de outras contas neste aparelho.",size=11,color=self.muted_color()),
                                self.appearance_previews(),
                                ft.Button("Escolher visual do Nex",icon=ft.Icons.PALETTE_OUTLINED,on_click=self.nex_skin_dialog),
                                ft.Dropdown(label="Seu visual",value=self.preferences.get("visual_style", "original"),
                                    options=[ft.DropdownOption(key=key,text=style["label"]) for key,style in VISUAL_STYLES.items()],
                                    on_select=lambda e:self.choose_visual_style(e.control.value)),
                                ft.Switch(label="Modo escuro", value=bool(self.preferences.get("dark_mode", True)),
                                          on_change=lambda e:self.toggle_dark_mode(e.control.value)),
                            ])
                        ),
                        ft.Container(
                            padding=15,bgcolor=self.surface_color(),border_radius=16,
                            border=ft.Border.all(1,self.border_color()),
                            content=ft.Column(spacing=7,controls=[
                                ft.Text("Privacidade e dados",size=16,weight=ft.FontWeight.BOLD),
                                ft.Text("O NexGrana usa os dados financeiros da família para cálculos, análises e recursos solicitados. Links de afiliado são externos e não recebem seu saldo, despesas ou histórico pelo app.",size=10,color=self.muted_color()),
                                ft.Text("Nunca armazene número completo de cartão, CVV, senha bancária ou credenciais. O cache local pode conter cópias dos dados exibidos e deve ser removido em dispositivo compartilhado.",size=10,color=self.muted_color()),
                                ft.Row(wrap=True,controls=[
                                    ft.OutlinedButton("Limpar cache local",icon=ft.Icons.CLEANING_SERVICES_OUTLINED,on_click=lambda e:(self.cloud.clear_local_cache(),self.snack("Cache local removido. Os dados da nuvem foram preservados."))),
                                    ft.TextButton("Sobre links de afiliado",icon=ft.Icons.INFO_OUTLINE,on_click=lambda e:self.snack(AFFILIATE_DISCLOSURE)),
                                ])
                            ])
                        ),
                        ft.Container(
                            padding=15, bgcolor=self.surface_color(), border_radius=16,
                            border=ft.Border.all(1, self.border_color()),
                            content=ft.Column(controls=[
                                ft.Text("Fechamento semestral", size=16, weight=ft.FontWeight.BOLD),
                                ft.Text("Guarde um resumo do semestre para comparação sem apagar o histórico que sustenta o saldo contínuo.",size=11,color=self.muted_color()),
                                ft.Button("Revisar semestre selecionado",icon=ft.Icons.ARCHIVE_OUTLINED,on_click=self.semester_dialog),
                            ])
                        ),
                        ft.Container(
                            padding=15,
                            bgcolor=self.surface_color(),
                            border_radius=16,
                            border=ft.Border.all(1, self.border_color()),
                            content=ft.Column(
                                spacing=7,
                                controls=[
                                    ft.Text(
                                        "Backup de testes (.db)",
                                        size=16,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Text(
                                        "Gera uma cópia dos dados atuais da nuvem em SQLite. "
                                        "Use durante os testes para guardar checkpoints antes de alterações importantes.",
                                        size=11,
                                        color=self.muted_color(),
                                    ),
                                    ft.Button(
                                        "Gerar backup .db",
                                        icon=ft.Icons.BACKUP_OUTLINED,
                                        on_click=lambda e: self.page.run_task(self.export_backup_db, e),
                                    ),
                                ],
                            ),
                        ),
                        ft.Container(
                            padding=15,
                            bgcolor=self.warning_surface_color(),
                            border_radius=16,
                            border=ft.Border.all(1, ft.Colors.AMBER_200),
                            content=ft.Column(
                                spacing=7,
                                controls=[
                                    ft.Text(
                                        "Importação opcional do NexGrana antigo",
                                        size=16,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Text(
                                        "Use esta opção apenas para trazer seu histórico antigo. "
                                        "Depois da importação, os dados ficam na nuvem e não será "
                                        "necessário usar o .db no dia a dia.",
                                        size=11,
                                        color=ft.Colors.GREY_700,
                                    ),
                                    ft.Button(
                                        "Informações sobre importação legada",
                                        icon=ft.Icons.UPLOAD_FILE,
                                        on_click=self.pick_legacy_db,
                                    ),
                                ],
                            ),
                        ),
                        ft.Button("Privacidade e exportação",icon=ft.Icons.PRIVACY_TIP_OUTLINED,on_click=lambda e:self.privacy_dialog()),
                        ft.Button("Personalizar conversa com o Nex",icon=ft.Icons.RECORD_VOICE_OVER_OUTLINED,on_click=self.nex_preferences_dialog),
                        ft.Button("Nex Vivo",icon=ft.Icons.AUTO_AWESOME_OUTLINED,on_click=self.nex_vivo_dialog),
                        ft.Button("Central de tutoriais",icon=ft.Icons.HELP_OUTLINE,on_click=lambda e:self._go_tutorial("welcome")),
                        ft.Button("Sair da conta", icon=ft.Icons.LOGOUT, on_click=self.logout),
                    ]),
                ),
            ],
        )


    async def pick_legacy_db(self, e=None):
        self.snack("A migração legada deve preservar IDs e ser validada pelo administrador. A importação destrutiva anterior foi desativada.",True)


    def privacy_dialog(self):
        try:
            consents=self.cloud.get_privacy_consents()
        except Exception:
            self.snack('Não foi possível consultar suas preferências. Verifique a conexão antes de alterá-las.',True)
            return
        reminders=ft.Switch(value=bool(consents.get('reminders')),tooltip='Lembretes opcionais')
        external_ai=ft.Switch(value=bool(consents.get('external_ai')),tooltip='IA externa')
        affiliates=ft.Switch(value=bool(consents.get('affiliate_personalization')),tooltip='Personalização de ofertas')

        def consent_row(title,detail,control):
            return ft.Container(
                padding=10,
                border_radius=12,
                bgcolor=self.surface_alt_color(),
                content=ft.Row(vertical_alignment=ft.CrossAxisAlignment.START,controls=[
                    ft.Column(expand=True,spacing=3,controls=[
                        ft.Text(title,weight=ft.FontWeight.BOLD),
                        ft.Text(detail,size=10,color=self.muted_color()),
                    ]),
                    control,
                ]),
            )

        def save_consents(e):
            try:
                self.cloud.set_privacy_consent('reminders',bool(reminders.value))
                self.cloud.set_privacy_consent('external_ai',bool(external_ai.value))
                self.cloud.set_privacy_consent('affiliate_personalization',bool(affiliates.value))
                self.snack('Preferências de privacidade atualizadas.')
            except Exception:
                self.snack('Não consegui atualizar os consentimentos agora. Verifique a migração 0.18 e a conexão.',True)

        dialog_w, dialog_h = self.dialog_dimensions(740,690)
        gateway_ready=bool(getattr(getattr(self,"nex_engine",None),"gateway",None))
        d=ft.AlertDialog(
            bgcolor=self.surface_color(),
            title=ft.Row(controls=[
                ft.Text('Privacidade e seus dados',expand=True),
                ft.IconButton(ft.Icons.CLOSE,tooltip='Fechar',on_click=lambda e:self.page.pop_dialog()),
            ]),
            content=ft.Column(width=dialog_w,height=dialog_h,scroll=ft.ScrollMode.AUTO,controls=[
                ft.Text('Suas escolhas podem ser alteradas aqui quando quiser. As funções financeiras básicas não dependem das opções abaixo.',size=12),
                ft.Text('Opcional · desligado significa que o recurso não usa essa autorização.',size=11,color=self.muted_color()),
                ft.Container(padding=11,bgcolor=self.surface_alt_color(),border_radius=12,content=ft.Text(
                    ('Nex online: serviço configurado, depende da sua autorização.' if gateway_ready else
                     'Nex online: o serviço ainda não está configurado neste app.'),size=11)),
                consent_row('Lembretes opcionais da Trilha Nex','Permite lembretes de etapas que você ativar.',reminders),
                consent_row('Nex online · IA externa','Autoriza enviar sua pergunta e o contexto recente ao gateway. O serviço pode estar indisponível; dados financeiros do cliente não são tratados como extrato verificado.',external_ai),
                consent_row('Personalização de ofertas','Permite ordenar Achados por preferências explícitas; dados financeiros não são enviados ao parceiro.',affiliates),
                ft.Container(padding=10,bgcolor=self.surface_alt_color(),border_radius=12,content=ft.Column(spacing=4,controls=[
                    ft.Text('Essencial',weight=ft.FontWeight.BOLD),
                    ft.Text('Autenticação e registros financeiros usados no app; não são desligados por estes controles.',size=11),
                    ft.Text('Histórico recente do chat fica na sua conta para continuar conversas. Não existe um controle independente de histórico nesta versão.',size=10,color=self.muted_color()),
                    ft.Text('Analytics remoto está desligado nesta versão.',size=10,color=self.muted_color()),
                ])),
                ft.ExpansionTile(title='Ler explicação completa',bgcolor=self.surface_alt_color(),collapsed_bgcolor=self.surface_alt_color(),
                    controls=[ft.Container(padding=12,content=ft.Text(POLICY_TEXT,selectable=True,size=11))]),
                ft.Divider(),
                ft.Text('Exportação',size=16,weight=ft.FontWeight.BOLD),
                ft.Text('Salve uma cópia .db para consultar seus registros fora do app. Inclui finanças, metas, compras, listas e suas conversas do Nex. Integrantes de um espaço compartilhado podem aparecer nos registros financeiros aos quais você tem acesso.',size=11),
                ft.Text('O arquivo exportado não tem senha. Guarde-o em local privado; esta ação não apaga nada da nuvem.',size=10,color=self.muted_color()),
                ft.Button('Exportar dados',icon=ft.Icons.DOWNLOAD_OUTLINED,on_click=lambda e:self.page.run_task(self.export_backup_db)),
                ft.Divider(),
                ft.Text('Exclusão de conta',size=16,weight=ft.FontWeight.BOLD),
                ft.Text('Em espaço individual, você pode excluir sua conta e os dados do espaço após confirmar. Em espaço familiar, a exclusão exige atendimento para preservar os registros das outras pessoas.',size=11),
                ft.OutlinedButton('Excluir minha conta',icon=ft.Icons.DELETE_OUTLINE,on_click=self.delete_account_dialog),
            ]),
            actions=[ft.TextButton('Fechar',on_click=lambda e:self.page.pop_dialog()),
                     ft.Button('Salvar preferências',icon=ft.Icons.CHECK,on_click=save_consents)],
        )
        self.page.show_dialog(d)
