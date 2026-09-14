from ui.common import PRIORITIES, affordable_acquisitions, brl, ft, money, quote, quote_plus

class AcquisitionsScreen:
    def _acquisition_icon(self, name):
        q=self._norm(name)
        if any(k in q for k in ["ps5","playstation","xbox","game","gta"]): return ft.Icons.SPORTS_ESPORTS
        if any(k in q for k in ["tv","televis","monitor"]): return ft.Icons.TV
        if any(k in q for k in ["escova","dente","oral"]): return ft.Icons.HEALTH_AND_SAFETY
        if any(k in q for k in ["maqui","batom","perfume","cosmet"]): return ft.Icons.FACE_RETOUCHING_NATURAL
        if any(k in q for k in ["celular","iphone","smartphone"]): return ft.Icons.SMARTPHONE
        if any(k in q for k in ["notebook","pc","computador"]): return ft.Icons.COMPUTER
        return ft.Icons.SHOPPING_BAG_OUTLINED


    def _acquisition_safe_image(self, name):
        """Somente imagens de demonstração conhecidas/localmente seguras.
        Itens sensíveis/adultos ficam sem imagem e usam ícone.
        """
        q=self._norm(name)
        blocked=["sexo","sex","adult","18","vibrador","dildo","porn","arma","gun","rifle","maconha","cannabis"]
        if any(x in q for x in blocked):
            return None
        # A 0.16 prioriza estabilidade/offline: ícones são o fallback oficial.
        # Um provedor de imagens licenciado pode ser conectado depois sem quebrar os cards.
        return None


    def _acquisition_recommendation(self, items=None):
        items=self.cloud.list_acquisitions(True) if items is None else items
        rows,budget=affordable_acquisitions(items,self.dashboard_data(),self.cloud.list_goals(),self.preferences.get("minimum_reserve",0))
        if not rows:
            return "thinking", f"Eu esperaria. Nenhuma compra cabe na margem conservadora de {brl(budget)} após compromissos e reservas.", None
        best=rows[0]
        return "idle", f"{best['item']} cabe na margem conservadora de {brl(budget)}. Confira suas prioridades antes de comprar.", best


    def acquisition_store_dialog(self, row):
        stores=["Mercado Livre","Shopee","Magalu","Amazon","AliExpress"]
        controls=[
            ft.Text("Escolha onde pesquisar. O NexGrana abre a busca do item; preço e disponibilidade são confirmados na loja.", size=11, color=self.muted_color())
        ]
        for st in stores:
            controls.append(ft.ListTile(
                leading=ft.Icon(ft.Icons.SEARCH),
                title=ft.Text(st),
                on_click=lambda e, store=st, item=row.get("item",""): self.page.run_task(self.open_store_search, store, item)
            ))
        d=ft.AlertDialog(title=ft.Text(f"Comparar preços — {row.get('item','Item')}"),content=ft.Column(width=420,tight=True,controls=controls),actions=[ft.TextButton("Fechar",on_click=lambda e:self.page.pop_dialog())])
        self.page.show_dialog(d)


    def store_search_url(self, store, item):
        item = (item or "").strip()
        if store == "Mercado Livre":
            return "https://lista.mercadolivre.com.br/" + quote(item.replace(" ", "-"))
        if store == "Shopee":
            return "https://shopee.com.br/search?keyword=" + quote_plus(item)
        if store == "Magalu":
            return "https://www.magazineluiza.com.br/busca/" + quote(item.replace(" ", "-")) + "/"
        if store == "Amazon":
            return "https://www.amazon.com.br/s?k=" + quote_plus(item)
        if store == "AliExpress":
            # A rota direta do AliExpress muda com frequência; usamos uma busca web
            # limitada ao domínio para evitar páginas inexistentes.
            return "https://www.google.com/search?q=" + quote_plus("site:pt.aliexpress.com " + item)
        return "https://www.google.com/search?q=" + quote_plus(item)


    async def open_store_search(self, store, item):
        try:
            url = self.store_search_url(store, item)
            launcher = ft.UrlLauncher()
            await launcher.launch_url(url, mode=ft.LaunchMode.EXTERNAL_APPLICATION)
        except Exception as ex:
            self.snack(f"Não foi possível abrir {store}: {ex}", True)


    def acquisitions_screen(self):
        items=self.cloud.list_acquisitions(True)
        mood,rec_text,rec=self._acquisition_recommendation(items)
        hero=ft.Container(
            padding=14,border_radius=18,bgcolor="#17192B",border=ft.Border.all(1,"#393266"),
            content=ft.ResponsiveRow(vertical_alignment=ft.CrossAxisAlignment.CENTER,controls=[
                ft.Container(col={"xs":4,"sm":2},alignment=ft.Alignment.CENTER,content=ft.Image(src=self.nex_asset(mood,"card"),width=115,height=115,fit=ft.BoxFit.CONTAIN,gapless_playback=True)),
                ft.Container(col={"xs":8,"sm":10},content=ft.Column(spacing=5,controls=[
                    ft.Text("Nex recomenda agora",size=17,weight=ft.FontWeight.BOLD),
                    ft.Text(rec_text,size=11,color=self.muted_color()),
                    ft.Row(wrap=True,controls=[
                        ft.OutlinedButton("Perguntar ao Nex",icon=ft.Icons.AUTO_AWESOME,on_click=lambda e:self._start_nex_topic("Analise minhas aquisições e me diga qual faz mais sentido comprar agora.")),
                        ft.Button("Planejar a recomendação",icon=ft.Icons.TRACK_CHANGES,on_click=lambda e,row=rec:self.goal_dialog(prefill=row) if row else None) if rec else ft.Container(),
                    ])
                ]))
            ])
        )
        cards=[]
        for x in items:
            pct=min(float(x.get("saved") or 0)/max(float(x.get("estimated") or 1),1),1)
            member=(x.get("household_members") or {}).get("display_name","Família")
            priority_color={"Alta":ft.Colors.RED,"Média":ft.Colors.ORANGE,"Baixa":ft.Colors.BLUE}.get(x.get("priority"),ft.Colors.INDIGO)
            missing=max(float(x.get("estimated") or 0)-float(x.get("saved") or 0),0)
            icon=self._acquisition_icon(x.get("item",""))
            actions=ft.PopupMenuButton(items=[
                ft.PopupMenuItem(content=ft.Text("Editar"),on_click=lambda e,row=x:self.edit_acq_dialog(row)),
                ft.PopupMenuItem(content=ft.Text("Concluir"),on_click=lambda e,rid=x["id"]:self.finish_acq(rid)),
                ft.PopupMenuItem(content=ft.Text("Excluir"),on_click=lambda e,rid=x["id"]:self.delete_acq(rid)),
            ])
            cards.append(ft.Container(
                col={"xs":12,"md":6},padding=14,bgcolor=self.surface_color(),border_radius=18,border=ft.Border.all(1,self.border_color()),
                content=ft.Column(spacing=9,controls=[
                    ft.Row(vertical_alignment=ft.CrossAxisAlignment.START,controls=[
                        ft.Container(width=58,height=58,border_radius=16,bgcolor="#151A2E",alignment=ft.Alignment.CENTER,content=ft.Icon(icon,color="#8B7CFF",size=30)),
                        ft.Column(expand=True,spacing=2,controls=[
                            ft.Text(x.get("item") or "Aquisição",size=17,weight=ft.FontWeight.BOLD,max_lines=1,overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(f"{member} • Prioridade {x.get('priority','Média')}",size=10,color=priority_color,weight=ft.FontWeight.BOLD),
                            ft.Text(f"Faltam {brl(missing)}",size=10,color=self.muted_color()),
                        ]),
                        actions,
                    ]),
                    ft.ProgressBar(value=pct,color=priority_color),
                    ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN,controls=[
                        ft.Text(f"{brl(x.get('saved',0))} guardados",size=10),
                        ft.Text(f"Meta {brl(x.get('estimated',0))}",size=10),
                    ]),
                    ft.Text(x.get("note") or "Sem observação",size=10,color=self.muted_color(),max_lines=2,overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Row(wrap=True,controls=[
                        ft.Button("Comparar preços",icon=ft.Icons.SEARCH,on_click=lambda e,row=x:self.acquisition_store_dialog(row)),
                        ft.OutlinedButton("Planejar",icon=ft.Icons.TRACK_CHANGES,on_click=lambda e,row=x:self.goal_dialog(prefill=row)),
                        ft.TextButton("Perguntar ao Nex",icon=ft.Icons.AUTO_AWESOME,on_click=lambda e,item=x.get("item",""),aid=x.get("id"):self._start_nex_topic(f"Analise a aquisição {item} e diga se faz sentido comprar agora.",source="acquisition",entity_id=aid,action="evaluate_acquisition")),
                    ])
                ])
            ))
        return ft.Column(expand=True,controls=[
            self.header("Aquisições","Decida o que comprar, quando e com qual impacto no caixa"),
            ft.Container(padding=16,expand=True,content=ft.Column(scroll=ft.ScrollMode.AUTO,spacing=12,controls=[
                hero,
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN,controls=[
                    ft.Text("Seus objetivos de compra",size=18,weight=ft.FontWeight.BOLD),
                    ft.Button("Nova aquisição",icon=ft.Icons.ADD,on_click=self.acq_dialog),
                ]),
                ft.ResponsiveRow(spacing=10,run_spacing=10,controls=cards) if cards else ft.Container(padding=25,alignment=ft.Alignment.CENTER,content=ft.Text("Nenhuma aquisição ativa ainda.",color=self.muted_color()))
            ]))
        ])


    def edit_acq_dialog(self, row):
        member = ft.Dropdown(
            label="Pessoa",
            options=self.member_options(),
            width=320,
            value=str(row.get("member_id") or ""),
        )
        item = ft.TextField(label="Produto ou objetivo", value=row["item"])
        priority = ft.Dropdown(
            label="Prioridade",
            options=[ft.DropdownOption(x) for x in PRIORITIES],
            value=row["priority"],
        )
        estimated = ft.TextField(label="Valor estimado", value=str(row["estimated"]).replace(".", ","))
        saved = ft.TextField(label="Já guardado", value=str(row["saved"]).replace(".", ","))
        note = ft.TextField(label="Observação", value=row.get("note") or "")
        dialog = ft.AlertDialog(
            title=ft.Text("Editar aquisição"),
            content=ft.Column(tight=True, controls=[member, item, priority, estimated, saved, note]),
        )

        def save(e):
            try:
                self.cloud.update_acquisition(
                    row["id"],
                    member_id=member.value,
                    item=item.value.strip(),
                    priority=priority.value,
                    estimated=money(estimated.value),
                    saved=money(saved.value),
                    note=note.value or "",
                )
                self.page.pop_dialog()
                self.last_cloud_snapshot = None
                self.render()
            except Exception as ex:
                self.snack(f"Não foi possível editar a aquisição: {ex}", True)

        dialog.actions = [
            ft.TextButton("Cancelar", on_click=lambda e: self.page.pop_dialog()),
            ft.Button("Salvar alterações", on_click=save),
        ]
        self.page.show_dialog(dialog)


    def acq_dialog(self, e=None):
        member = ft.Dropdown(label="Pessoa", options=self.member_options(), width=320)
        if self.current_member():
            member.value = str(self.current_member()["id"])
        item = ft.TextField(label="Produto ou objetivo")
        priority = ft.Dropdown(label="Prioridade", options=[ft.DropdownOption(x) for x in PRIORITIES], value="Média")
        estimated = ft.TextField(label="Valor estimado")
        saved = ft.TextField(label="Já guardado", value="0")
        note = ft.TextField(label="Observação")
        dialog = ft.AlertDialog(title=ft.Text("Nova aquisição"), content=ft.Column(tight=True, controls=[member, item, priority, estimated, saved, note]))

        def save(e):
            try:
                self.cloud.add_acquisition(member.value, item.value, priority.value, money(estimated.value), money(saved.value), note.value or "")
                self.page.pop_dialog()
                self.render()
            except Exception as ex:
                self.snack(str(ex), True)
        dialog.actions = [ft.TextButton("Cancelar", on_click=lambda e: self.page.pop_dialog()), ft.Button("Salvar", on_click=save)]
        self.page.show_dialog(dialog)


    def finish_acq(self, rid):
        self.cloud.finish_acquisition(rid)
        self.last_cloud_snapshot = None
        self.render()


    def delete_acq(self, rid):
        self.cloud.delete_acquisition(rid)
        self.last_cloud_snapshot = None
        self.render()


