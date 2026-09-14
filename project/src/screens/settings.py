from ui.common import AFFILIATE_DISCLOSURE, POLICY_TEXT, asyncio, brl, defaultdict, export_snapshot, ft, logger, money, storage_dir, uuid, write_backup

class SettingsScreen:
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

        return ft.Column(
            expand=True, scroll=ft.ScrollMode.ALWAYS,
            controls=[
                self.header("Mais", "Configurações, conta, segurança e dados"),
                ft.Container(
                    padding=16,
                    content=ft.Column(spacing=12, controls=[
                        family_info,
                        ft.Container(
                            padding=15, bgcolor=self.surface_color(), border_radius=16,
                            border=ft.Border.all(1, self.border_color()),
                            content=ft.Column(controls=[
                                ft.Text("Sincronização", size=16, weight=ft.FontWeight.BOLD),
                                ft.Text("Cloud ativo: Windows e Android usam o mesmo banco online. O .db antigo não é carregado automaticamente."),
                                ft.Text(f"Última atualização: {self.last_sync}"),
                            ]),
                        ),
                        ft.Container(
                            padding=15, bgcolor=self.surface_color(), border_radius=16,
                            border=ft.Border.all(1, self.border_color()),
                            content=ft.Column(controls=[
                                ft.Text("Aparência", size=16, weight=ft.FontWeight.BOLD),
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
            consents={}
        reminders=ft.Switch(label='Lembretes opcionais da Trilha Nex',value=bool(consents.get('reminders')))
        external_ai=ft.Switch(label='Permitir IA externa quando esse recurso existir',value=bool(consents.get('external_ai')))
        affiliates=ft.Switch(label='Personalização opcional de ofertas afiliadas',value=bool(consents.get('affiliate_personalization')))

        def save_consents(e):
            try:
                self.cloud.set_privacy_consent('reminders',bool(reminders.value))
                self.cloud.set_privacy_consent('external_ai',bool(external_ai.value))
                self.cloud.set_privacy_consent('affiliate_personalization',bool(affiliates.value))
                self.snack('Preferências de privacidade atualizadas.')
            except Exception:
                self.snack('Não consegui atualizar os consentimentos agora. Verifique a migração 0.18 e a conexão.',True)

        dialog_w, dialog_h = self.dialog_dimensions(620,560)
        d=ft.AlertDialog(
            title=ft.Text('Privacidade e seus dados'),
            content=ft.Column(width=dialog_w,height=dialog_h,scroll=ft.ScrollMode.AUTO,controls=[
                ft.Text(POLICY_TEXT,selectable=True,size=11),
                ft.Divider(),
                ft.Text('Consentimentos opcionais',size=16,weight=ft.FontWeight.BOLD),
                ft.Text('Desativar uma opção não bloqueia os controles financeiros básicos. IA externa ainda não está conectada nesta versão.',size=10,color=self.muted_color()),
                reminders,external_ai,affiliates,
                ft.Button('Salvar consentimentos',icon=ft.Icons.PRIVACY_TIP_OUTLINED,on_click=save_consents),
                ft.Divider(),
                ft.Text('Exportação',size=16,weight=ft.FontWeight.BOLD),
                ft.Text('A exportação inclui os registros do espaço que sua conta tem permissão para consultar.',size=10,color=self.muted_color()),
                ft.Button('Exportar dados',icon=ft.Icons.DOWNLOAD_OUTLINED,on_click=lambda e:self.page.run_task(self.export_backup_db)),
                ft.Container(padding=10,border_radius=12,bgcolor=self.warning_surface_color(),content=ft.Text('Exclusão completa de conta ainda exige backend administrativo seguro. O NexGrana não exibe um botão de exclusão falsa/destrutiva.',size=10)),
            ]),
            actions=[ft.TextButton('Fechar',on_click=lambda e:self.page.pop_dialog())]
        )
        self.page.show_dialog(d)


