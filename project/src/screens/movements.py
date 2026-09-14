from ui.common import CATEGORIES, KINDS, brl, datetime, day, defaultdict, expense_batch, expense_status, ft, money, month_label, parse_date, split_amount

class MovementsScreen:
    def income_screen(self):
        rows = self.cloud.list_income(self.month)
        member = ft.Dropdown(label="Pessoa", options=self.member_options(), width=280)
        cm = self.current_member()
        if cm:
            member.value = str(cm["id"])
        amount = ft.TextField(label="Valor da renda", width=220, keyboard_type=ft.KeyboardType.NUMBER)
        received = ft.TextField(label="Data real de recebimento", value=datetime.now().strftime("%d/%m/%Y"), hint_text="dd/mm/aaaa")
        note = ft.TextField(label="Origem / observação", expand=True)

        def save_income(e):
            try:
                if not member.value:
                    self.snack("Selecione a pessoa.", True)
                    return
                value = money(amount.value)
                if value <= 0:
                    self.snack("Informe uma renda maior que zero.", True)
                    return
                self.cloud.add_income(member.value, value, self.month, note.value or "", received_at=day(received.value).isoformat())
                amount.value = ""
                note.value = ""
                self.last_sync = datetime.now().strftime("%H:%M:%S")
                self.last_cloud_snapshot = None
                self.render()
            except Exception as ex:
                self.snack(f"Não foi possível registrar a renda: {ex}", True)

        cards = []
        for x in rows:
            person = (x.get("household_members") or {}).get("display_name", "—")
            cards.append(
                ft.Container(
                    padding=12,
                    bgcolor=self.surface_color(),
                    border_radius=14,
                    border=ft.Border.all(1, self.border_color()),
                    content=ft.Row(
                        controls=[
                            ft.Icon(ft.Icons.PAYMENTS, color=ft.Colors.GREEN),
                            ft.Column(
                                expand=True,
                                spacing=2,
                                controls=[
                                    ft.Text(person, weight=ft.FontWeight.BOLD),
                                    ft.Text(x.get("note") or "Sem observação", size=11, color=self.muted_color()),
                                ],
                            ),
                            ft.Text(brl(x["amount"]), weight=ft.FontWeight.BOLD),
                            ft.IconButton(
                                icon=ft.Icons.EDIT_OUTLINED,
                                tooltip="Editar renda",
                                on_click=lambda e, row=x: self.edit_income_dialog(row),
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                tooltip="Excluir renda",
                                on_click=lambda e, rid=x["id"]: self.delete_income(rid),
                            ),
                        ],
                    ),
                )
            )

        return ft.Column(
            expand=True,
            controls=[
                self.header("Registrar renda", "Renda mensal por pessoa"),
                ft.Container(
                    padding=16,
                    expand=True,
                    content=ft.Column(
                        scroll=ft.ScrollMode.AUTO,
                        spacing=12,
                        controls=[
                            ft.Container(
                                padding=15,
                                bgcolor=self.surface_color(),
                                border_radius=16,
                                border=ft.Border.all(1, self.border_color()),
                                content=ft.ResponsiveRow(
                                    controls=[
                                        ft.Container(col={"xs": 12, "md": 3}, content=member),
                                        ft.Container(col={"xs": 12, "md": 3}, content=amount),
                                        ft.Container(col={"xs": 12, "md": 4}, content=ft.Column(controls=[received,note])),
                                        ft.Container(
                                            col={"xs": 12, "md": 2},
                                            content=ft.Button("Salvar renda", icon=ft.Icons.ADD, on_click=save_income),
                                        ),
                                    ]
                                ),
                            ),
                            ft.Text(f"Rendas de {month_label(self.month)}", size=16, weight=ft.FontWeight.BOLD),
                            *cards,
                        ],
                    ),
                ),
            ],
        )


    def edit_income_dialog(self, row):
        member = ft.Dropdown(label="Pessoa", options=self.member_options(), width=330, value=str(row["member_id"]))
        amount = ft.TextField(label="Valor", value=str(row["amount"]).replace(".", ","), keyboard_type=ft.KeyboardType.NUMBER)
        received = ft.TextField(label="Data real de recebimento", value=(day(row["received_at"]).strftime("%d/%m/%Y") if row.get("received_at") else ""), hint_text="dd/mm/aaaa")
        note = ft.TextField(label="Origem / observação", value=row.get("note") or "")
        dialog = ft.AlertDialog(
            title=ft.Text("Editar renda"),
            content=ft.Column(tight=True, controls=[member, amount, received, note]),
        )

        def save(e):
            try:
                self.cloud.update_income(row["id"], member.value, money(amount.value), self.month, note.value or "", received_at=day(received.value).isoformat())
                self.page.pop_dialog()
                self.last_cloud_snapshot = None
                self.render()
            except Exception as ex:
                self.snack(f"Não foi possível editar a renda: {ex}", True)

        dialog.actions = [
            ft.TextButton("Cancelar", on_click=lambda e: self.page.pop_dialog()),
            ft.Button("Salvar alterações", on_click=save),
        ]
        self.page.show_dialog(dialog)


    def delete_income(self, row_id):
        try:
            self.cloud.delete_income(row_id)
            self.last_cloud_snapshot = None
            self.render()
        except Exception as ex:
            self.snack(f"Não foi possível excluir a renda: {ex}", True)


    def income_dialog(self, e=None):
        member = ft.Dropdown(label="Pessoa", options=self.member_options(), width=330)
        cm = self.current_member()
        if cm:
            member.value = str(cm["id"])
        amount = ft.TextField(label="Valor", keyboard_type=ft.KeyboardType.NUMBER)
        received = ft.TextField(label="Data real de recebimento", value=datetime.now().strftime("%d/%m/%Y"), hint_text="dd/mm/aaaa")
        note = ft.TextField(label="Origem / observação")
        dialog = ft.AlertDialog(
            title=ft.Text("Adicionar renda"),
            content=ft.Column(tight=True, controls=[member, amount, received, note]),
        )
        def save(e):
            try:
                self.cloud.add_income(member.value, money(amount.value), self.month, note.value or "", received_at=day(received.value).isoformat())
                self.page.pop_dialog()
                self.last_sync = datetime.now().strftime("%H:%M:%S")
                self.render()
            except Exception as ex:
                self.snack(str(ex), True)
        dialog.actions = [ft.TextButton("Cancelar", on_click=lambda e: self.page.pop_dialog()), ft.Button("Salvar", on_click=save)]
        self.page.show_dialog(dialog)


    def expenses_screen(self):
        expenses = self.cloud.list_expenses(self.month)
        members = self.members()
        names = ["Todos"] + [m["display_name"] for m in members]

        person_filter = ft.Dropdown(
            label="Pessoa",
            value=self.expense_person_filter if self.expense_person_filter in names else "Todos",
            width=180,
            options=[ft.DropdownOption(x) for x in names],
        )
        order = ft.Dropdown(
            label="Ordem",
            value=self.expense_order,
            width=190,
            options=[
                ft.DropdownOption(key="recent", text="Mais recentes primeiro"),
                ft.DropdownOption(key="old", text="Mais antigas primeiro"),
            ],
        )
        group = ft.Checkbox(label="Agrupar por pessoa", value=self.expense_group)

        def apply_filters(e=None):
            self.expense_person_filter = person_filter.value or "Todos"
            self.expense_order = order.value or "recent"
            self.expense_group = bool(group.value)
            self.render()

        person_filter.on_select = apply_filters
        order.on_select = apply_filters
        group.on_change = apply_filters

        def payer_name(x):
            return (x.get("household_members") or {}).get("display_name", "—")

        if self.expense_person_filter != "Todos":
            expenses = [x for x in expenses if payer_name(x) == self.expense_person_filter]

        def date_key(x):
            try:
                return parse_date(x["expense_date"])
            except Exception:
                return datetime.min

        expenses = sorted(expenses, key=date_key, reverse=self.expense_order == "recent")
        total_filtered = sum(float(x["amount"]) for x in expenses)

        member_color = {}
        palette = [ft.Colors.INDIGO, ft.Colors.PURPLE, ft.Colors.BLUE, ft.Colors.TEAL, ft.Colors.ORANGE, ft.Colors.PINK, ft.Colors.CYAN]
        for i, m in enumerate(members):
            member_color[m["display_name"]] = palette[i % len(palette)]

        def expense_card(x):
            payer = payer_name(x)
            color = member_color.get(payer, ft.Colors.GREY)
            return ft.Container(
                padding=12, bgcolor=self.surface_color(), border_radius=14,
                border=ft.Border.all(1, self.border_color()),
                content=ft.Row(controls=[
                    ft.Container(width=5, height=52, border_radius=5, bgcolor=color),
                    ft.Container(
                        width=44, height=44, border_radius=12,
                        bgcolor=ft.Colors.with_opacity(.10, color),
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(ft.Icons.RECEIPT_LONG, color=color),
                    ),
                    ft.Column(expand=True, spacing=2, controls=[
                        ft.Text(x["description"], weight=ft.FontWeight.BOLD),
                        ft.Text({"scheduled":"Agendada","paid":"Paga","overdue":"Atrasada","cancelled":"Cancelada"}[expense_status(x)],size=10),
                        ft.Text(f"{x['category']} • {x['kind']} • {payer}", size=11, color=self.muted_color()),
                        ft.Text(
                            f"{x['expense_date']} • {x['installment_number']}/{x['installments_total']}"
                            if x["installments_total"] > 1 else x["expense_date"],
                            size=10, color=self.subtle_color(),
                        ),
                    ]),
                    ft.Text(brl(x["amount"]), weight=ft.FontWeight.BOLD),
                    ft.PopupMenuButton(items=[
                        ft.PopupMenuItem(content=ft.Text("Confirmar pagamento"),on_click=lambda e,row=x:self.payment_dialog(row)),
                        ft.PopupMenuItem(content=ft.Text("Editar"),on_click=lambda e,row=x:self.edit_expense_dialog(row)),
                        ft.PopupMenuItem(content=ft.Text("Cancelar lançamento"),on_click=lambda e,row=x:self.payment_dialog(row,cancel=True)),
                        ft.PopupMenuItem(content=ft.Text("Excluir"),on_click=lambda e,rid=x["id"]:self.delete_expense(rid)),
                    ]),
                ]),
            )

        rows = []
        if self.expense_group:
            grouped = defaultdict(list)
            for x in expenses:
                grouped[payer_name(x)].append(x)
            for person in [m["display_name"] for m in members]:
                person_rows = grouped.get(person, [])
                if not person_rows:
                    continue
                subtotal = sum(float(x["amount"]) for x in person_rows)
                rows.append(ft.Container(
                    padding=ft.Padding.only(top=10),
                    content=ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                        ft.Text(person, size=17, weight=ft.FontWeight.BOLD, color=member_color.get(person)),
                        ft.Text(brl(subtotal), weight=ft.FontWeight.BOLD),
                    ])
                ))
                rows.extend(expense_card(x) for x in person_rows)
        else:
            rows = [expense_card(x) for x in expenses]

        return ft.Column(
            expand=True,
            controls=[
                self.header("Despesas", "Filtre por integrante, período e ordem"),
                ft.Container(
                    padding=16, expand=True,
                    content=ft.Column(
                        scroll=ft.ScrollMode.ALWAYS,
                        spacing=10,
                        controls=[
                            ft.ResponsiveRow(controls=[
                                ft.Container(col={"xs":12,"sm":4}, content=person_filter),
                                ft.Container(col={"xs":12,"sm":4}, content=order),
                                ft.Container(col={"xs":12,"sm":4}, content=group),
                            ]),
                            ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                                ft.Column(spacing=1, controls=[
                                    ft.Text(f"{len(expenses)} lançamentos"),
                                    ft.Text(f"Total filtrado: {brl(total_filtered)}", weight=ft.FontWeight.BOLD),
                                ]),
                                ft.Button("Nova despesa", icon=ft.Icons.ADD, on_click=self.expense_dialog),
                            ]),
                            *rows,
                        ],
                    ),
                ),
            ],
        )


    def edit_expense_dialog(self, row):
        members = self.members()
        payer = ft.Dropdown(
            label="Quem pagou?",
            options=self.member_options(),
            width=320,
            value=str(row.get("payer_member_id") or ""),
        )
        kind = ft.Dropdown(label="Tipo", options=[ft.DropdownOption(x) for x in KINDS], value=row["kind"])
        category = ft.Dropdown(label="Categoria", options=[ft.DropdownOption(x) for x in CATEGORIES], value=row["category"])
        desc = ft.TextField(label="Descrição", value=row["description"])
        amount = ft.TextField(label="Valor", value=str(row["amount"]).replace(".", ","), keyboard_type=ft.KeyboardType.NUMBER)
        date = ft.TextField(label="Data", value=row["expense_date"])
        split = ft.Dropdown(
            label="Divisão",
            options=[ft.DropdownOption("Somente quem pagou"), ft.DropdownOption("Igual entre todos")],
            value="Igual entre todos" if len(row.get("expense_shares") or []) > 1 else "Somente quem pagou",
        )
        info = ft.Text(
            "Em parcelamentos, esta edição altera somente a parcela selecionada.",
            size=10, color=self.muted_color(),
        )
        dialog = ft.AlertDialog(
            title=ft.Text("Editar despesa"),
            content=ft.Column(
                tight=True, scroll=ft.ScrollMode.AUTO,
                controls=[payer, kind, category, desc, amount, date, split, info],
            ),
        )

        def save(e):
            try:
                total = money(amount.value)
                dt = parse_date(date.value)
                mm = dt.strftime("%m/%Y")
                if split.value == "Igual entre todos" and members:
                    shares = split_amount(total, [mbr["id"] for mbr in members])
                else:
                    shares = [(payer.value, total)]
                self.cloud.update_expense(
                    row["id"], payer.value, kind.value, category.value, desc.value,
                    total, date.value, mm, bool(row.get("automatic_debit")), shares,
                )
                self.page.pop_dialog()
                self.last_cloud_snapshot = None
                self.render()
            except Exception as ex:
                self.snack(f"Não foi possível editar a despesa: {ex}", True)

        dialog.actions = [
            ft.TextButton("Cancelar", on_click=lambda e: self.page.pop_dialog()),
            ft.Button("Salvar alterações", on_click=save),
        ]
        self.page.show_dialog(dialog)


    def delete_expense(self, row_id):
        try:
            self.cloud.delete_expense(row_id)
            self.last_cloud_snapshot = None
            self.render()
        except Exception as ex:
            self.snack(str(ex), True)


    def expense_dialog(self, e=None):
        members = self.members()
        payer = ft.Dropdown(label="Quem pagou?", options=self.member_options(), width=320)
        if self.current_member():
            payer.value = str(self.current_member()["id"])
        kind = ft.Dropdown(label="Tipo", options=[ft.DropdownOption(x) for x in KINDS], value="Variável")
        category = ft.Dropdown(label="Categoria", options=[ft.DropdownOption(x) for x in CATEGORIES], value="Outros")
        desc = ft.TextField(label="Descrição")
        amount = ft.TextField(label="Valor de cada parcela", keyboard_type=ft.KeyboardType.NUMBER)
        automatic = ft.Checkbox(label="Débito automático no vencimento", value=False)
        date_field = ft.TextField(label="Data", value=datetime.now().strftime("%d/%m/%Y"))
        installments = ft.TextField(label="Parcelas", value="1", keyboard_type=ft.KeyboardType.NUMBER)
        split = ft.Dropdown(
            label="Divisão",
            options=[ft.DropdownOption("Somente quem pagou"), ft.DropdownOption("Igual entre todos")],
            value="Somente quem pagou",
        )
        dialog = ft.AlertDialog(
            title=ft.Text("Registrar despesa"),
            content=ft.Column(tight=True, scroll=ft.ScrollMode.AUTO,
                              controls=[payer, kind, category, desc, amount, date_field, installments, automatic, split]),
        )

        pending_batch = None
        def do_save(close_after):
            nonlocal pending_batch
            try:
                if pending_batch is None:
                    pending_batch=expense_batch(self.cloud._hid(),payer.value,kind.value,category.value,desc.value,
                        money(amount.value),date_field.value,int(installments.value or '1'),automatic.value,
                        [m['id'] for m in members] if split.value=='Igual entre todos' else [payer.value])
                self.cloud.client.rpc('save_expense_batch',{'p_rows':pending_batch,'p_replace':False}).execute()
                pending_batch=None
                self.last_cloud_snapshot = None
                self.last_sync = datetime.now().strftime("%H:%M:%S")
                if close_after:
                    self.page.pop_dialog()
                    self.render()
                else:
                    # Mantém pagador, data, tipo e categoria para lançamento em sequência.
                    desc.value = ""
                    amount.value = ""
                    installments.value = "1"
                    desc.focus()
                    dialog.update()
                    self.snack("Despesa registrada. Pronto para a próxima.")
            except Exception:
                self.snack("Não foi possível confirmar o salvamento. Tente novamente com os mesmos dados; o identificador impede duplicação.", True)

        dialog.actions = [
            ft.TextButton("Cancelar", on_click=lambda e: self.page.pop_dialog()),
            ft.OutlinedButton("Salvar e novo", icon=ft.Icons.ADD, on_click=lambda e: do_save(False)),
            ft.Button("Salvar e fechar", icon=ft.Icons.CHECK, on_click=lambda e: do_save(True)),
        ]
        self.page.show_dialog(dialog)


    def payment_dialog(self, row, cancel=False):
        paid=ft.TextField(label="Data do pagamento",value=datetime.now().strftime("%d/%m/%Y"),visible=not cancel)
        d=ft.AlertDialog(title=ft.Text("Cancelar lançamento" if cancel else "Confirmar pagamento"),content=ft.Column(tight=True,controls=[ft.Text(f"{row['description']} • {brl(row['amount'])}"),paid]))
        def save(e):
            try:
                self.cloud.set_payment(row['id'],'cancelled' if cancel else 'paid',paid.value)
                self.page.pop_dialog();self.render()
            except Exception as exc:self.snack(str(exc),True)
        d.actions=[ft.TextButton("Voltar",on_click=lambda e:self.page.pop_dialog()),ft.Button("Confirmar",on_click=save)]
        self.page.show_dialog(d)


