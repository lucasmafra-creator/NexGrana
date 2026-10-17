from ui.common import AFFILIATE_DISCLOSURE, active_offers, asyncio, brl, fc, filter_offers, ft, money
from services.offers import validate_partner_url
from services.affiliate import HOSTS
from services.market import product_values, receipt_comparison, budget_summary
from services.product_scan import available as product_ocr_available, scan_photo

class MarketScreen:
    RECEIPT_PHOTO_LIMIT = 6
    RECEIPT_TOTAL_BYTES_LIMIT = 18 * 1024 * 1024

    def _shopping_lists_panel(self):
        if not hasattr(self.cloud,"list_shopping_lists"):
            return ft.Text("Listas pessoais disponíveis quando a migração 0.24 estiver instalada.")
        try:
            lists=self.cloud.list_shopping_lists()
        except Exception:
            return ft.Container(padding=12,content=ft.Text(
                "Listas indisponíveis. Confira a migração 0.24 e tente sincronizar novamente.",color=ft.Colors.ORANGE_300))
        name=ft.TextField(label="Nova lista",hint_text="Ex.: compra do mês",dense=True)
        budget=ft.TextField(label="Orçamento opcional",hint_text="Ex.: 900,00",dense=True)
        def create(_):
            try:
                self.cloud.add_shopping_list(name.value,money(budget.value or 0),self.active_member_id)
                self.render()
            except Exception as exc:self.snack(f"Não foi possível criar a lista: {exc}",True)
        controls=[ft.Text("Suas listas",size=19,weight=ft.FontWeight.BOLD),
            ft.Text("Prepare compras antes de ir ao caixa. A lista não lança despesas nem abre links de afiliados.",size=11,color=self.muted_color()),
            ft.ResponsiveRow(spacing=8,run_spacing=8,controls=[
                ft.Container(col={"xs":12,"sm":6},content=name),
                ft.Container(col={"xs":12,"sm":3},content=budget),
                ft.Container(col={"xs":12,"sm":3},content=ft.Button("Criar lista",on_click=create))])]
        if not lists:
            controls.append(ft.Text("Nenhuma lista ainda. Crie uma para acompanhar itens, valores e orçamento."))
        selected=next((row for row in lists if str(row["id"])==str(getattr(self,"_shopping_list_id",""))),None)
        if selected is None and lists:selected=lists[0]
        if lists:
            controls.append(ft.Row(wrap=True,controls=[ft.OutlinedButton(
                (row.get("name") or "Lista")+ (" ✓" if row==selected else ""),
                on_click=lambda _,rid=row["id"]:self._select_shopping_list(rid)) for row in lists[:10]]))
        if selected:
            owned=str(selected.get("created_by") or "")==str(getattr(self.cloud.user,"id","") or "")
            controls.append(ft.Row(controls=[
                ft.Text(selected.get("name") or "Lista",weight=ft.FontWeight.BOLD,size=16,expand=True,max_lines=1,overflow=ft.TextOverflow.ELLIPSIS),
                ft.IconButton(ft.Icons.EDIT_OUTLINED,tooltip="Editar lista",visible=owned,
                    on_click=lambda _,r=selected:self._edit_shopping_list(r)),
                ft.IconButton(ft.Icons.DELETE_OUTLINE,tooltip="Excluir lista",visible=owned,
                    on_click=lambda _,r=selected:self._delete_shopping_list_dialog(r)),
            ]))
            try:items=self.cloud.list_shopping_list_items(selected["id"])
            except Exception:
                controls.append(ft.Text("Itens indisponíveis: não foi possível confirmar esta lista. Tente sincronizar novamente.",color=ft.Colors.ORANGE_300))
                return ft.Container(padding=15,bgcolor=self.surface_color(),border_radius=16,
                                    border=ft.Border.all(1,self.border_color()),content=ft.Column(spacing=8,controls=controls))
            total=sum(float(row.get("quantity") or 0)*float(row.get("unit_price") or 0) for row in items)
            spent=sum(float(row.get("quantity") or 0)*float(row.get("unit_price") or 0) for row in items if row.get("purchased"))
            missing=sum(1 for row in items if not row.get("purchased"))
            budget_value=float(selected.get("budget") or 0)
            unknown=sum(1 for row in items if not float(row.get("unit_price") or 0))
            summary=f"{len(items)-missing} comprado(s) · {missing} faltando · Gasto marcado: {brl(spent)} · Previsão de todos os itens: {brl(total)}"
            if budget_value:summary+=f" · Restante após comprados: {brl(budget_value-spent)}"
            if unknown:summary+=f" · {unknown} item(ns) sem preço — total parcial"
            controls.append(ft.Container(padding=12,bgcolor=self.surface_alt_color(),border_radius=12,content=ft.Text(summary,weight=ft.FontWeight.BOLD)))
            if owned:
                controls.append(ft.Button("Iniciar compra com esta lista",icon=ft.Icons.SHOPPING_CART_CHECKOUT,
                    on_click=lambda _,r=selected:self._start_list_trip_dialog(r)))
            for row in items:
                def change_checked(e,item=row):
                    try:self.cloud.update_shopping_list_item(item["id"],purchased=bool(e.control.value));self.render()
                    except Exception as exc:self.snack(f"Não foi possível atualizar: {exc}",True)
                def remove(e,item=row):
                    try:self.cloud.delete_shopping_list_item(item["id"]);self.render()
                    except Exception as exc:self.snack(f"Não foi possível remover: {exc}",True)
                controls.append(ft.Row(controls=[
                    ft.Checkbox(value=bool(row.get("purchased")),on_change=change_checked),
                    ft.Text(f"{row.get('name')} · {row.get('quantity')} × {brl(row.get('unit_price') or 0)}",expand=True,max_lines=2,overflow=ft.TextOverflow.ELLIPSIS),
                    ft.IconButton(ft.Icons.EDIT_OUTLINED,tooltip="Editar produto",on_click=lambda _,r=row:self._edit_shopping_list_item(r)),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE,tooltip="Remover da lista",on_click=remove)]))
            product=ft.TextField(label="Produto",hint_text="Ex.: arroz",dense=True)
            quantity=ft.TextField(label="Quantidade",value="1",dense=True)
            price=ft.TextField(label="Preço estimado",hint_text="Opcional",dense=True)
            def add_item(_):
                try:
                    self.cloud.add_shopping_list_item(selected["id"],product.value,quantity.value, money(price.value or 0))
                    self.render()
                except Exception as exc:self.snack(f"Não foi possível adicionar: {exc}",True)
            controls.append(ft.ResponsiveRow(spacing=8,run_spacing=8,controls=[
                ft.Container(col={"xs":12,"sm":5},content=product),
                ft.Container(col={"xs":5,"sm":2},content=quantity),
                ft.Container(col={"xs":7,"sm":2},content=price),
                ft.Container(col={"xs":12,"sm":3},content=ft.Button("Adicionar item",on_click=add_item))]))
        return ft.Container(padding=15,bgcolor=self.surface_color(),border_radius=16,
                            border=ft.Border.all(1,self.border_color()),content=ft.Column(spacing=8,controls=controls))

    def _select_shopping_list(self,list_id):
        self._shopping_list_id=str(list_id)
        self.render()

    def _start_list_trip_dialog(self,row):
        market=ft.TextField(label="Em qual mercado você vai comprar?",autofocus=True)
        def start(_):
            try:
                self.cloud.start_market_trip_from_list(row["id"],market.value)
                self.page.pop_dialog();self.render()
            except Exception as exc:self.snack(f"Não consegui iniciar a compra: {exc}",True)
        self.page.show_dialog(ft.AlertDialog(title=ft.Text("Comprar itens da lista"),
            content=ft.Column(tight=True,controls=[
                ft.Text("Os itens são copiados para esta compra. A lista original continua como planejamento; marque somente o que colocar no carrinho."),market]),
            actions=[ft.TextButton("Cancelar",on_click=lambda _:self.page.pop_dialog()),ft.Button("Iniciar compra",on_click=start)]))

    def _edit_shopping_list(self,row):
        name=ft.TextField(label="Nome",value=row.get("name") or "")
        budget=ft.TextField(label="Orçamento",value=str(row.get("budget") or 0).replace(".",","))
        def save(_):
            try:
                self.cloud.update_shopping_list(row["id"],name.value,money(budget.value or 0))
                self.page.pop_dialog();self.render()
            except Exception as exc:self.snack(f"Não foi possível editar a lista: {exc}",True)
        self.page.show_dialog(ft.AlertDialog(bgcolor=self.surface_color(),title=ft.Text("Editar lista"),
            content=ft.Column(width=self.dialog_dimensions(440,390)[0],tight=True,controls=[name,budget]),
            actions=[ft.TextButton("Cancelar",on_click=lambda _:self.page.pop_dialog()),ft.Button("Salvar",on_click=save)]))

    def _delete_shopping_list_dialog(self,row):
        def remove(_):
            try:
                self.cloud.delete_shopping_list(row["id"])
                self._shopping_list_id=""
                self.page.pop_dialog();self.render()
            except Exception as exc:self.snack(f"Não foi possível excluir a lista: {exc}",True)
        self.page.show_dialog(ft.AlertDialog(bgcolor=self.surface_color(),title=ft.Text("Excluir lista?"),
            content=ft.Text("Os itens desta lista também serão removidos. Isso não registra nem apaga despesas financeiras."),
            actions=[ft.TextButton("Cancelar",on_click=lambda _:self.page.pop_dialog()),ft.Button("Excluir lista",on_click=remove)]))

    def _edit_shopping_list_item(self,row):
        name=ft.TextField(label="Produto",value=row.get("name") or "")
        qty=ft.TextField(label="Quantidade",value=str(row.get("quantity") or 1).replace(".",","))
        price=ft.TextField(label="Preço estimado",value=str(row.get("unit_price") or 0).replace(".",","))
        def save(_):
            try:
                self.cloud.update_shopping_list_item(row["id"],name=name.value,quantity=qty.value,
                                                      unit_price=money(price.value or 0))
                self.page.pop_dialog();self.render()
            except Exception as exc:self.snack(f"Não foi possível editar o item: {exc}",True)
        self.page.show_dialog(ft.AlertDialog(bgcolor=self.surface_color(),title=ft.Text("Editar produto"),
            content=ft.Column(width=self.dialog_dimensions(440,410)[0],tight=True,controls=[name,qty,price]),
            actions=[ft.TextButton("Cancelar",on_click=lambda _:self.page.pop_dialog()),ft.Button("Salvar",on_click=save)]))

    def _achados_panel(self, offers):
        categories=["Todos"]+sorted({str(row.get("category") or "Outros") for row in offers})
        query=ft.TextField(
            hint_text="Pesquisar nos Achados",
            prefix_icon=ft.Icons.SEARCH,
            expand=True,
            dense=True,
        )
        category=ft.Dropdown(
            label="Categoria",
            value="Todos",
            width=210,
            dense=True,
            options=[ft.DropdownOption(value) for value in categories],
        )
        results=ft.Column(spacing=8)
        count=ft.Text("",size=10,color=self.muted_color())

        def rebuild(e=None):
            rows=filter_offers(offers,query.value,category.value)
            count.value=f"{len(rows)} achado(s)"
            results.controls.clear()
            if not rows:
                results.controls.append(ft.Container(
                    padding=16,
                    border_radius=14,
                    bgcolor=self.surface_alt_color(),
                    content=ft.Column(horizontal_alignment=ft.CrossAxisAlignment.CENTER,controls=[
                        ft.Icon(ft.Icons.SEARCH_OFF_OUTLINED,color="#8B7CFF"),
                        ft.Text("Nenhum achado corresponde a esses filtros.",text_align=ft.TextAlign.CENTER),
                        ft.Text("Tente outra palavra ou selecione Todas as categorias.",size=10,color=self.muted_color()),
                    ]),
                ))
            for row in rows:
                results.controls.append(ft.Container(
                    padding=12,border_radius=14,bgcolor=self.surface_alt_color(),
                    border=ft.Border.all(1,self.border_color()),
                    content=ft.ResponsiveRow(vertical_alignment=ft.CrossAxisAlignment.CENTER,controls=[
                        ft.Container(col={"xs":2,"sm":1},content=ft.Icon(ft.Icons.LOCAL_OFFER_OUTLINED,color="#8B7CFF")),
                        ft.Container(col={"xs":10,"sm":8},content=ft.Column(spacing=2,controls=[
                            ft.Text(row.get("title") or "Oferta",weight=ft.FontWeight.BOLD),
                            ft.Text(row.get("subtitle") or "Preço e condições no parceiro.",size=10,color=self.muted_color()),
                            ft.Text((brl(row.get("price")) if row.get("price") is not None else "Preço indisponível — consulte no parceiro"),size=9,weight=ft.FontWeight.BOLD),
                            ft.Text(("Preço informado pela fonte em "+str(row.get("verified_at"))) if row.get("verified_at") else "Confira preço e estoque na loja.",size=8,color=self.muted_color()),
                            ft.Text("Link de afiliado declarado" if row.get("affiliate") else "Link externo do parceiro",size=8,color=self.muted_color()),
                            ft.Text(f"{row.get('category','Outros')} • {row.get('provider','Parceiro')} • Link externo",size=8,color="#8B7CFF"),
                        ])),
                        ft.Container(col={"xs":12,"sm":3},content=ft.Button(
                            "Ver oferta",icon=ft.Icons.OPEN_IN_NEW,
                            on_click=lambda e,item=row:self._open_offer(item,"achados"),
                        )),
                    ]),
                ))
            try:
                count.update();results.update()
            except Exception:
                pass

        query.on_change=rebuild
        category.on_select=rebuild
        rebuild()
        return ft.Container(
            padding=15,bgcolor=self.surface_color(),border_radius=18,
            border=ft.Border.all(1,"#3B3566"),
            content=ft.Column(spacing=9,controls=[
                ft.Row(controls=[ft.Icon(ft.Icons.SAVINGS_OUTLINED,color="#8B7CFF"),ft.Text("Achados NexGrana",size=17,weight=ft.FontWeight.BOLD)]),
                ft.Text(AFFILIATE_DISCLOSURE,size=9,color=self.muted_color()),
                ft.ResponsiveRow(spacing=8,run_spacing=8,controls=[
                    ft.Container(col={"xs":12,"sm":8},content=query),
                    ft.Container(col={"xs":12,"sm":4},content=category),
                ]),
                count,results,
            ]),
        )

    def _open_offer(self, offer, origin="market"):
        """Registra somente metadados comerciais permitidos e abre o parceiro.

        Analytics remoto permanece desativado por padrão; nenhum valor financeiro,
        texto de compra ou identificador familiar entra no evento.
        """
        if not validate_partner_url(offer.get("url"),set(getattr(self.cloud,"_offer_partner_hosts",HOSTS))):
            self.snack("Link não autorizado. Atualize o catálogo antes de abrir.",True)
            return
        try:
            self.analytics.track(
                "offer_clicked",
                offer_id=str(offer.get("id") or offer.get("offer_id") or "unknown"),
                origin=str(origin),
                campaign=str(offer.get("campaign") or "") or None,
            )
        except Exception:
            pass
        self.page.run_task(self.open_external_url, offer.get("url"))

    def _add_receipt_photos(self, photos):
        """Adiciona fotos temporárias da nota com limites previsíveis de memória."""
        accepted = 0
        rejected = 0
        current = sum(len(getattr(p, "bytes", b"") or b"") for p in getattr(self, "receipt_photos", []))
        for photo in photos or []:
            data = getattr(photo, "bytes", None)
            if not data:
                rejected += 1
                continue
            if len(self.receipt_photos) >= self.RECEIPT_PHOTO_LIMIT:
                rejected += 1
                continue
            if current + len(data) > self.RECEIPT_TOTAL_BYTES_LIMIT:
                rejected += 1
                continue
            self.receipt_photos.append(photo)
            current += len(data)
            accepted += 1
        return accepted, rejected

    def market_edit_trip_dialog(self, trip):
        name=ft.TextField(label="Mercado",value=trip.get("market_name") or "")
        budget=ft.TextField(label="Orçamento",value=str(trip.get("budget") or 0).replace(".",","),keyboard_type=ft.KeyboardType.NUMBER)
        history=ft.Text("O limite da compra é separado das despesas. Alterações confirmadas ficam no histórico.",size=11,color=self.muted_color())
        async def load_history(e=None):
            try:
                rows=await asyncio.to_thread(self.cloud.market_budget_history,trip['id'])
                rows=sorted(rows,key=lambda r:str(r.get('created_at') or ''),reverse=True)[:5]
                history.value="\n".join(f"{str(r.get('created_at') or '')[:10]}: {brl(r['old_budget'])} → {brl(r['new_budget'])}" for r in rows) or "Nenhuma alteração sincronizada neste histórico."
            except Exception:
                history.value="Histórico indisponível. Confira a conexão e a migration 0.25.2 no ambiente de teste."
            self.page.update()
        d=ft.AlertDialog(title=ft.Text("Editar compra"),content=ft.Column(tight=True,controls=[name,budget,history,
            ft.TextButton("Consultar histórico do limite",on_click=lambda e:self.page.run_task(load_history,e))]))
        def persist():
            try:
                result=self.cloud.update_market_trip(trip["id"],market_name=name.value.strip(),budget=money(budget.value or 0))
                self.page.pop_dialog();self.render()
                self.snack("Compra atualizada." if result.get('_sync_state')=='synced' else "Alteração salva no aparelho; aguardando sincronização. O histórico remoto será criado quando confirmar.")
            except Exception:
                self.snack("Não consegui atualizar. Confira nome, limite não negativo, conexão e migration 0.25.2; se houve conflito, atualize a compra.",True)
        def save(e):
            try:
                value=money(budget.value or 0)
                if not name.value.strip() or value<0:raise ValueError()
            except Exception:
                self.snack("Informe mercado e limite não negativo.",True);return
            if value==money(trip.get('budget') or 0):persist();return
            confirmation=ft.AlertDialog(title=ft.Text("Confirmar novo limite"),content=ft.Text(
                f"De {brl(trip.get('budget') or 0)} para {brl(value)}. Isso altera o planejamento desta compra; as despesas anteriores continuam com os valores registrados."))
            def confirm(e):self.page.pop_dialog();persist()
            confirmation.actions=[ft.TextButton("Voltar",on_click=lambda e:self.page.pop_dialog()),ft.Button("Confirmar",on_click=confirm)]
            self.page.show_dialog(confirmation)
        d.actions=[ft.TextButton("Cancelar",on_click=lambda e:self.page.pop_dialog()),ft.Button("Salvar",on_click=save)]
        self.page.show_dialog(d)


    def market_edit_item_dialog(self, item):
        product=ft.TextField(label="Produto",value=item.get("product_name") or "")
        qty=ft.TextField(label="Quantidade",value=str(item.get("quantity") or 1).replace(".",","),keyboard_type=ft.KeyboardType.NUMBER)
        price=ft.TextField(label="Preço unitário",value=str(item.get("unit_price") or 0).replace(".",","),keyboard_type=ft.KeyboardType.NUMBER)
        category=ft.Dropdown(label="Categoria",value=item.get("category") or "Outros",options=[ft.DropdownOption(x) for x in ["Alimentação","Carnes","Higiene","Limpeza","Bebidas","Doces/snacks","Pet","Casa","Outros"]])
        d=ft.AlertDialog(title=ft.Text("Editar produto"),content=ft.Column(width=460,tight=True,controls=[product,qty,price,category]))
        def save(e):
            try:
                name, quantity, value = product_values(product.value, qty.value, money(price.value))
                self.cloud.update_market_item(item["id"],product_name=name,quantity=float(quantity),unit_price=float(value),category=category.value)
                self.page.pop_dialog();self.render()
            except Exception as ex:self.snack(str(ex),True)
        d.actions=[ft.TextButton("Cancelar",on_click=lambda e:self.page.pop_dialog()),ft.Button("Salvar",on_click=save)]
        self.page.show_dialog(d)


    def market_screen(self):
        tab=getattr(self,"_market_tab","Compras")
        width=max(300,min(960,float(self.page.width or 960)-32))
        def content_area(rows):
            return ft.Container(expand=True,bgcolor=self.page_color(),padding=8,
                content=ft.Row(alignment=ft.MainAxisAlignment.CENTER,vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[ft.Container(width=width,expand=False,content=ft.Column(
                        expand=True,scroll=ft.ScrollMode.AUTO,spacing=12,controls=rows))]))
        def choose_tab(value):
            self._market_tab=value
            self.render()
        switch=ft.Row(wrap=True,controls=[
            ft.Button("Compras e listas",on_click=lambda _:choose_tab("Compras")) if tab=="Compras" else
                ft.OutlinedButton("Compras e listas",on_click=lambda _:choose_tab("Compras")),
            ft.Button("Achados · links externos",on_click=lambda _:choose_tab("Achados")) if tab=="Achados" else
                ft.OutlinedButton("Achados · links externos",on_click=lambda _:choose_tab("Achados")),
        ])
        if tab=="Achados":
            raw_offers=self.cloud.list_affiliate_offers()
            offers=active_offers(raw_offers,allowed_hosts=getattr(self.cloud,"_offer_partner_hosts",HOSTS))
            return ft.Column(expand=True,controls=[
                self.header("Achados","Ofertas externas com busca e filtros; nenhuma compra é lançada aqui"),
                ft.Container(padding=12,content=switch),
                content_area([self._achados_panel(offers) if offers else ft.Text("Nenhuma oferta disponível agora. Confira depois.")]),
            ])
        trips=self.cloud.list_market_trips()
        active=next((x for x in trips if x.get("status")=="open"),None)
        controls=[ft.OutlinedButton("Desfazer última alteração",icon=ft.Icons.UNDO,on_click=self._undo_market_ui),self._shopping_lists_panel()]
        if active:
            items=self.cloud.list_market_items(active["id"])
            planned=sum(float(x.get("unit_price") or 0)*float(x.get("quantity") or 0) for x in items)
            total=sum(float(x.get("unit_price") or 0)*float(x.get("quantity") or 0)
                      for x in items if not x.get("source_list_item_id") or x.get("picked"))
            budget=float(active.get("budget") or 0)
            item_rows=[]
            for x in items[-40:]:
                def mark_picked(e,row=x):
                    try:self.cloud.update_market_item(row["id"],picked=bool(e.control.value));self.render()
                    except Exception as exc:self.snack(f"Não foi possível marcar o produto: {exc}",True)
                item_rows.append(ft.Container(
                    padding=10,border_radius=12,bgcolor=self.surface_alt_color(),
                    content=ft.Row(controls=[
                        ft.Checkbox(value=bool(x.get("picked")),tooltip="Coloquei no carrinho",on_change=mark_picked)
                            if x.get("source_list_item_id") else ft.Icon(ft.Icons.SHOPPING_BASKET_OUTLINED,color="#8B7CFF"),
                        ft.Column(expand=True,spacing=1,controls=[
                            ft.Text(x.get("product_name") or "Produto",weight=ft.FontWeight.BOLD),
                            ft.Text(f"{float(x.get('quantity') or 0):g} × {brl(x.get('unit_price') or 0)} • {x.get('category') or 'Sem categoria'}",size=9,color=self.muted_color())
                        ]),
                        ft.Text(brl(float(x.get('quantity') or 0)*float(x.get('unit_price') or 0)),weight=ft.FontWeight.BOLD),
                        ft.PopupMenuButton(items=[
                            ft.PopupMenuItem(content=ft.Text("Editar"),on_click=lambda e,row=x:self.market_edit_item_dialog(row)),
                            ft.PopupMenuItem(content=ft.Text("Excluir"),on_click=lambda e,rid=x["id"]:self._delete_market_item(rid)),
                        ])
                    ])
                ))
            controls.append(ft.Container(
                padding=15,bgcolor=self.surface_color(),border_radius=18,border=ft.Border.all(1,self.border_color()),
                content=ft.Column(spacing=10,controls=[
                    ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN,controls=[
                        ft.Column(expand=True,spacing=2,controls=[
                            ft.Text(f"Compra em andamento — {active.get('market_name') or 'Mercado'}",size=18,weight=ft.FontWeight.BOLD),
                            ft.Text(f"{len(items)} tipo(s) • No carrinho {brl(total)}" +
                                (f" • Lista prevista {brl(planned)}" if active.get('source_list_id') else "") +
                                (f" • Restante {brl(budget-total)}" if budget else ""),size=11,color=self.muted_color()),
                        ]),
                        ft.PopupMenuButton(items=[
                            ft.PopupMenuItem(content=ft.Text("Editar compra"),on_click=lambda e,t=active:self.market_edit_trip_dialog(t)),
                            ft.PopupMenuItem(content=ft.Text("Excluir compra"),on_click=lambda e,rid=active["id"]:self._delete_market_trip(rid)),
                        ])
                    ]),
                    ft.ProgressBar(value=min(total/max(budget,1),1) if budget else 0,color=ft.Colors.GREEN if not budget or total<=budget else ft.Colors.RED),
                    ft.Row(wrap=True,controls=[
                        ft.Button("Adicionar produto",icon=ft.Icons.ADD_SHOPPING_CART,on_click=lambda e,t=active:self.market_item_dialog(t)),
                        ft.OutlinedButton("Conferir nota / finalizar",icon=ft.Icons.RECEIPT_LONG,on_click=lambda e,t=active:self.market_finish_dialog(t)),
                    ]),
                    *item_rows
                ])
            ))
        else:
            controls.append(ft.Container(padding=18,bgcolor=self.surface_color(),border_radius=18,border=ft.Border.all(1,self.border_color()),content=ft.ResponsiveRow(vertical_alignment=ft.CrossAxisAlignment.CENTER,controls=[
                ft.Container(col={"xs":4,"sm":2},alignment=ft.Alignment.CENTER,content=ft.Image(src=self.nex_asset("thinking","card",context="market"),width=115,height=115,fit=ft.BoxFit.CONTAIN)),
                ft.Container(col={"xs":8,"sm":10},content=ft.Column(spacing=6,controls=[
                    ft.Text("Comece uma compra",size=18,weight=ft.FontWeight.BOLD),
                    ft.Text("Registre produtos, compare o carrinho com a nota e crie um histórico real de preços para comprar melhor nas próximas vezes.",size=11,color=self.muted_color()),
                    ft.Button("Nova compra",icon=ft.Icons.SHOPPING_CART_CHECKOUT,on_click=self.market_new_dialog),
                ]))
            ])))
        closed=[x for x in trips if x.get("status")=="closed"][:8]
        if closed:
            controls.append(ft.Text("Compras anteriores",size=17,weight=ft.FontWeight.BOLD))
            for t in closed:
                controls.append(ft.ListTile(
                    leading=ft.Icon(ft.Icons.RECEIPT),
                    title=ft.Text(t.get("market_name") or "Mercado"),
                    subtitle=ft.Text(f"{t.get('shopping_date','')} • carrinho {brl(t.get('cart_total',0))} • nota {brl(t.get('receipt_total',0))}"),
                    trailing=ft.PopupMenuButton(items=[
                        ft.PopupMenuItem(content=ft.Text("Ver e corrigir produtos"),on_click=lambda e,row=t:self.market_history_dialog(row)),
                        ft.PopupMenuItem(content=ft.Text("Editar compra"),on_click=lambda e,row=t:self.market_edit_trip_dialog(row)),
                        ft.PopupMenuItem(content=ft.Text("Conferir nota novamente"),on_click=lambda e,row=t:self.market_finish_dialog(row)),
                        ft.PopupMenuItem(content=ft.Text("Excluir compra"),on_click=lambda e,rid=t['id']:self._delete_market_trip(rid)),
                    ]),
                    on_click=lambda e,row=t:self.market_history_dialog(row),
                ))

        return ft.Column(expand=True,controls=[
            self.header("Mercado","Compras, listas e histórico; Achados fica em sua própria aba"),
            ft.Container(padding=12,content=switch),
            content_area(controls)
        ])


    def _undo_market_ui(self,e=None):
        try:
            result=self.cloud.undo_market_action()
            self.render()
            self.snack("Ação desfeita." if result.get('_sync_state')=='synced' else "Desfazer salvo no aparelho; sincronização pendente.")
        except Exception as exc:self.snack(str(exc),True)

    def _delete_market_item(self, rid):
        try:
            self.cloud.delete_market_item(rid);self.render()
            self.snack('Produto removido. Use Desfazer última alteração para recuperar.')
        except Exception as ex:self.snack(f"Não foi possível excluir o produto: {ex}",True)

    def market_history_dialog(self, trip):
        items=self.cloud.list_market_items(trip['id'])
        rows=[]
        def edit(row):
            self.page.pop_dialog()
            self.market_edit_item_dialog(row)
        def remove(row):
            self.page.pop_dialog()
            self._delete_market_item(row['id'])
        for row in items:
            rows.append(ft.ListTile(
                title=ft.Text(row.get('product_name') or 'Produto'),
                subtitle=ft.Text(f"{row.get('quantity')} × {brl(row.get('unit_price'))}"),
                trailing=ft.PopupMenuButton(items=[
                    ft.PopupMenuItem(content=ft.Text('Editar'),on_click=lambda e,r=row:edit(r)),
                    ft.PopupMenuItem(content=ft.Text('Excluir'),on_click=lambda e,r=row:remove(r)),
                ]),
            ))
        def add(e):
            self.page.pop_dialog()
            self.market_item_dialog(trip)
        self.page.show_dialog(ft.AlertDialog(
            title=ft.Text(trip.get('market_name') or 'Compra'),
            content=ft.Column(width=520,tight=True,scroll=ft.ScrollMode.AUTO,controls=rows or [ft.Text('Sem produtos registrados.')]),
            actions=[ft.TextButton('Fechar',on_click=lambda e:self.page.pop_dialog()),ft.Button('Adicionar produto',on_click=add)],
        ))


    def _delete_market_trip(self, rid):
        try:
            self.cloud.delete_market_trip(rid);self.render()
            self.snack('Compra removida do histórico. Despesas já lançadas continuam em Despesas. Você pode desfazer.')
        except Exception as ex:self.snack(f"Não foi possível excluir a compra: {ex}",True)


    def market_new_dialog(self,e=None):
        name=ft.TextField(label="Mercado",autofocus=True); budget=ft.TextField(label="Orçamento (opcional)",keyboard_type=ft.KeyboardType.NUMBER)
        d=ft.AlertDialog(title=ft.Text("Nova compra"),content=ft.Column(tight=True,controls=[name,budget]))
        def save(e):
            if not name.value.strip(): self.snack("Informe o mercado.",True); return
            try:
                self.cloud.add_market_trip(name.value,money(budget.value or 0)); self.page.pop_dialog(); self.render()
            except Exception as ex:self.snack(f"Atualize o patch do Supabase para usar Mercado: {ex}",True)
        d.actions=[ft.TextButton("Cancelar",on_click=lambda e:self.page.pop_dialog()),ft.Button("Começar",on_click=save)]; self.page.show_dialog(d)


    def market_item_dialog(self,trip,e=None):
        product=ft.TextField(label="Produto",autofocus=True)
        qty=ft.TextField(label="Quantidade",value="1",keyboard_type=ft.KeyboardType.NUMBER,col={"xs":12,"sm":6},hint_text="Ex.: 1 ou 1,5")
        price=ft.TextField(label="Preço unitário",keyboard_type=ft.KeyboardType.NUMBER,col={"xs":12,"sm":6},hint_text="Ex.: 12,90")
        category=ft.Dropdown(label="Categoria",value="Alimentação",options=[ft.DropdownOption(x) for x in ["Alimentação","Carnes","Higiene","Limpeza","Bebidas","Doces/snacks","Pet","Casa","Outros"]])
        status=ft.Text("",visible=False,size=11)
        remaining=ft.Text(size=12,weight=ft.FontWeight.BOLD)
        def refresh_budget():
            try:
                data=budget_summary(self.cloud.list_market_items(trip["id"]),trip.get("budget") or 0)
                remaining.value=f"Gasto nesta compra: {brl(data['spent'])}"+(f" • Restante do limite: {brl(data['remaining'])}" if data['remaining'] is not None else " • Sem limite definido")
                remaining.color=ft.Colors.ORANGE_400 if data["remaining"] is not None and data["remaining"]<0 else self.muted_color()
            except Exception:
                remaining.value="Não consegui atualizar o resumo da compra; nenhum valor foi estimado."
        refresh_budget()
        saving={"busy":False}
        async def suggest_photo(e):
            picker=ft.FilePicker();self.page.services.append(picker)
            try:
                files=await picker.pick_files(allow_multiple=False,file_type=ft.FilePickerFileType.IMAGE,with_data=True)
                if not files:return
                data=getattr(files[0],"bytes",None)
                if not data:raise ValueError("Não consegui acessar a foto selecionada")
                status.visible=True;status.value="Lendo a foto neste dispositivo…";self.page.update()
                suggestions=await asyncio.to_thread(scan_photo,data)
                if not suggestions:
                    self.snack("Não identifiquei produto e preço com confiança. Registre manualmente.");return
                def use(candidate):
                    product.value=candidate["name"];price.value=candidate["unit_price"].replace(".",",")
                    self.page.pop_dialog();self.page.update()
                    self.snack("Sugestão preenchida. Confira nome, quantidade e preço antes de adicionar.")
                self.page.show_dialog(ft.AlertDialog(title=ft.Text("Confira a sugestão da foto"),content=ft.Column(tight=True,controls=[
                    ft.Text("OCR local pode errar; nada foi cadastrado ainda.",size=11),
                    *[ft.TextButton(f"{c['name']} • R$ {c['unit_price']} • leitura {c['confidence']}%",on_click=lambda e,item=c:use(item)) for c in suggestions],
                ]),actions=[ft.TextButton("Cancelar",on_click=lambda e:self.page.pop_dialog())]))
            except Exception as exc:self.snack(str(exc),True)
            finally:
                status.visible=False;self.page.update()
                if picker in self.page.services:self.page.services.remove(picker)
        cancel_button=ft.TextButton("Cancelar")
        continue_button=ft.OutlinedButton("Adicionar e continuar")
        add_button=ft.Button("Adicionar")
        dialog_w,dialog_h=self.dialog_dimensions(560,680)
        d=ft.AlertDialog(
            title=ft.Row(controls=[
                ft.Text("Adicionar produto",expand=True),
                ft.IconButton(ft.Icons.CLOSE,tooltip="Fechar",on_click=lambda e:self.page.pop_dialog()),
            ]),
        )

        def set_busy(value):
            for button in (cancel_button,continue_button,add_button):
                button.disabled=value
            status.visible=value
            status.value="Salvando…" if value else ""
            self.page.update()

        async def save(e, keep=False):
            if saving["busy"]:return
            if not product.value.strip(): self.snack("Informe o produto.",True); return
            saving["busy"]=True
            set_busy(True)
            try:
                name, q, v = product_values(product.value, qty.value or '1', money(price.value))
                await asyncio.to_thread(self.cloud.add_market_item,trip['id'],name,float(q),float(v),category.value)
                refresh_budget()
                if keep:
                    product.value=""; qty.value="1"; price.value=""; self.page.update()
                    await product.focus()
                    self.snack("Produto adicionado. Continue a compra.")
                else:
                    self.page.pop_dialog(); self.render()
            except Exception as ex:
                self.snack(str(ex),True)
                set_busy(False)
            finally:
                saving["busy"]=False
                if keep:
                    set_busy(False)

        cancel_button.on_click=lambda e:self.page.pop_dialog()
        continue_button.on_click=lambda e:self.page.run_task(save,e,True)
        add_button.on_click=lambda e:self.page.run_task(save,e,False)
        price.on_submit=lambda e:self.page.run_task(save,e,True)
        d.content=ft.Column(
            width=dialog_w,
            height=dialog_h,
            scroll=ft.ScrollMode.AUTO,
            spacing=12,
            controls=[
                remaining,
                ft.Text("O limite da compra é um planejamento, separado do saldo financeiro.",size=10,color=self.muted_color()),
                ft.OutlinedButton("Sugerir por foto",icon=ft.Icons.PHOTO_CAMERA_OUTLINED,on_click=suggest_photo),
                ft.Text("Leitura local disponível" if product_ocr_available() else "OCR local não instalado neste dispositivo. Você pode continuar pela entrada manual.",size=10,color=self.muted_color()),
                product,
                ft.ResponsiveRow(spacing=8,run_spacing=8,controls=[qty,price]),
                category,
                status,
                ft.Divider(),
                ft.Text("Escolha uma ação",size=12,weight=ft.FontWeight.BOLD),
                ft.ResponsiveRow(spacing=8,run_spacing=8,controls=[
                    ft.Container(col={"xs":12,"sm":4},content=cancel_button),
                    ft.Container(col={"xs":12,"sm":4},content=continue_button),
                    ft.Container(col={"xs":12,"sm":4},content=add_button),
                ]),
                ft.Text("Adicionar salva e fecha. Adicionar e continuar salva uma vez e limpa o formulário.",size=10,color=self.muted_color()),
            ],
        )
        self.page.show_dialog(d)


    async def open_receipt_camera(self, photo_status=None, thumbs=None):
        """Câmera nativa no Android; em plataformas sem suporte cai para seletor de imagens."""
        platform=str(getattr(self.page,"platform","")).lower()
        if fc is None or "android" not in platform:
            try:
                picker=ft.FilePicker()
                if picker not in self.page.services:self.page.services.append(picker)
                files=await picker.pick_files(dialog_title="Selecione fotos da nota",allow_multiple=True,with_data=True,file_type=ft.FilePickerFileType.IMAGE,compression_quality=78)
                if files:
                    accepted, rejected = self._add_receipt_photos(files)
                    if rejected:
                        self.snack(f"{rejected} imagem(ns) ignorada(s). Limite: {self.RECEIPT_PHOTO_LIMIT} fotos / 18 MB.", True)
                    if photo_status:
                        photo_status.value=f"{len(self.receipt_photos)} imagem(ns) prontas"
                        photo_status.color=ft.Colors.GREEN_700
                        photo_status.update()
                    if thumbs:
                        import base64
                        thumbs.controls.clear()
                        for f in self.receipt_photos[:4]:
                            thumbs.controls.append(ft.Image(src="data:image/jpeg;base64,"+base64.b64encode(f.bytes).decode(),width=64,height=64,fit=ft.BoxFit.COVER,border_radius=8))
                        thumbs.update()
                return
            except Exception as ex:
                self.snack(f"Não foi possível abrir imagens: {ex}",True);return
        try:
            camera=fc.Camera(expand=True,preview_enabled=True)
            status=ft.Text("Enquadre a nota inteira e evite reflexos.",size=10,color=self.muted_color())
            dialog_w, dialog_h = self.dialog_dimensions(520,560)
            d=ft.AlertDialog(title=ft.Text("Fotografar nota"),content=ft.Column(width=dialog_w,height=dialog_h,controls=[
                ft.Container(expand=True,bgcolor=ft.Colors.BLACK,border_radius=16,content=camera),
                status
            ]))
            async def capture(e=None):
                try:
                    data=await camera.take_picture()
                    if data:
                        class Photo:
                            bytes=data
                            name="camera.jpg"
                        accepted, rejected = self._add_receipt_photos([Photo()])
                        if rejected:
                            self.snack(f"Limite de {self.RECEIPT_PHOTO_LIMIT} fotos ou 18 MB atingido.", True)
                            return
                        if thumbs is not None:
                            import base64
                            thumbs.controls.append(ft.Image(src="data:image/jpeg;base64,"+base64.b64encode(data).decode(),width=64,height=64,fit=ft.BoxFit.COVER,border_radius=8))
                            thumbs.update()
                        if photo_status:
                            photo_status.value=f"{len(self.receipt_photos)} foto(s) capturada(s)"
                            photo_status.color=ft.Colors.GREEN_700
                        self.page.pop_dialog()
                        self.snack("Foto adicionada. Você pode capturar outras partes da nota.")
                        if photo_status:photo_status.update()
                except Exception as ex:self.snack(f"Falha ao fotografar: {ex}",True)
            capture_button=ft.Button("Capturar",disabled=True,icon=ft.Icons.CAMERA_ALT,on_click=lambda e:self.page.run_task(capture,e))
            d.actions=[ft.TextButton("Cancelar",on_click=lambda e:self.page.pop_dialog()),capture_button]
            self.page.show_dialog(d)
            self.page.update()
            # Native methods require a mounted control with an assigned control ID.
            cameras=await camera.get_available_cameras()
            if not cameras:
                raise RuntimeError("Nenhuma câmera disponível")
            chosen=next((c for c in cameras if "back" in str(getattr(c,"lens_direction","")).lower()),cameras[0])
            await camera.initialize(description=chosen,resolution_preset=fc.ResolutionPreset.HIGH,enable_audio=False,image_format_group=fc.ImageFormatGroup.JPEG)
            capture_button.disabled=False
            capture_button.update()
        except Exception as ex:
            self.snack(f"Câmera indisponível neste dispositivo: {ex}",True)


    def market_finish_dialog(self,trip,e=None):
        from datetime import date
        self.receipt_photos = []
        post_expense=ft.Checkbox(label="Lançar o total da nota como despesa no perfil selecionado",value=False)
        expense_date=ft.TextField(label="Data da despesa (AAAA-MM-DD)",value=str(trip.get('shopping_date') or date.today().isoformat()))
        member_id=str(self.active_member_id or '')
        items=self.cloud.list_market_items(trip["id"])
        cart=receipt_comparison(items,0)["cart"]
        receipt=ft.TextField(label="Total da nota",hint_text="Ex.: 132,40",keyboard_type=ft.KeyboardType.NUMBER)
        cashback=ft.TextField(label="Cashback realmente recebido",hint_text="0,00",value="0",keyboard_type=ft.KeyboardType.NUMBER)
        photo_status=ft.Text("Nenhuma imagem adicionada",size=10,color=self.muted_color())
        thumbs=ft.Row(wrap=True,spacing=6)
        async def pick_photos(e=None):
            try:
                picker=ft.FilePicker()
                if picker not in self.page.services:self.page.services.append(picker)
                files=await picker.pick_files(dialog_title="Câmera / galeria — fotos da nota",allow_multiple=True,with_data=True,file_type=ft.FilePickerFileType.IMAGE,compression_quality=78)
                if files:
                    accepted, rejected = self._add_receipt_photos(files)
                    if rejected:
                        self.snack(f"{rejected} imagem(ns) ignorada(s). Limite: {self.RECEIPT_PHOTO_LIMIT} fotos / 18 MB.", True)
                    photo_status.value=f"{len(self.receipt_photos)} imagem(ns) prontas para conferência"
                    photo_status.color=ft.Colors.GREEN_700
                    thumbs.controls.clear()
                    for f in self.receipt_photos:
                        import base64
                        src="data:image/jpeg;base64,"+base64.b64encode(f.bytes).decode()
                        thumbs.controls.append(ft.Image(src=src,width=64,height=64,fit=ft.BoxFit.COVER,border_radius=8))
                    photo_status.update();thumbs.update()
            except Exception as ex:self.snack(f"Não foi possível abrir câmera/galeria: {ex}",True)
        help_box=ft.Container(padding=10,border_radius=12,bgcolor=self.surface_alt_color(),content=ft.Text("📷 No Android, use a câmera ou a galeria. Até 6 imagens (18 MB no total) ficam apenas durante a conferência. O NexGrana não cria itens automaticamente: qualquer leitura futura da nota precisará ser confirmada por você.",size=10,color=self.muted_color()))
        cashback_help=ft.Container(padding=10,border_radius=12,bgcolor=self.surface_alt_color(),content=ft.Text("💡 Cashback é dinheiro devolvido depois da compra. Ele não muda o total fiscal da nota. Informe somente o valor que realmente recebeu.",size=10,color=self.muted_color()))
        d=ft.AlertDialog(
            title=ft.Text("Conferir compra"),
            content=ft.Column(width=520,tight=True,scroll=ft.ScrollMode.AUTO,spacing=10,controls=[
                ft.Text(f"Soma registrada no carrinho: {brl(cart)}",weight=ft.FontWeight.BOLD),
                ft.Row(wrap=True,controls=[
                    ft.Button("Câmera",icon=ft.Icons.CAMERA_ALT_OUTLINED,on_click=lambda e:self.page.run_task(self.open_receipt_camera,photo_status,thumbs)),
                    ft.OutlinedButton("Galeria",icon=ft.Icons.PHOTO_LIBRARY_OUTLINED,on_click=lambda e:self.page.run_task(pick_photos,e)),
                ]),
                photo_status,thumbs,help_box,receipt,cashback,cashback_help,post_expense,expense_date,
                ft.Text("A despesa usa o total da nota. Cashback não é descontado nem vira renda automaticamente. O saldo segue a data da despesa.",size=10),
                ft.TextButton("Ver opções de cashback no Méliuz",icon=ft.Icons.OPEN_IN_NEW,on_click=lambda e:self.page.run_task(self.open_external_url,"https://www.meliuz.com.br/"))
            ])
        )
        def finish(e):
            try:
                if not str(receipt.value or '').strip():
                    raise ValueError("Informe o total da nota")
                comparison=receipt_comparison(self.cloud.list_market_items(trip["id"]),money(receipt.value),money(cashback.value or 0))
                selected_date=date.fromisoformat(str(expense_date.value).strip()).isoformat() if post_expense.value else None
                should_post=bool(post_expense.value)
                if should_post and (not member_id or comparison['receipt']<=0):raise ValueError('Selecione um perfil e informe nota maior que zero para lançar despesa.')
                confirm=ft.AlertDialog(title=ft.Text("Confirmar valores conferidos"),content=ft.Column(tight=True,controls=[
                    ft.Text(f"Carrinho: {brl(comparison['cart'])}"),
                    ft.Text(f"Nota: {brl(comparison['receipt'])}"),
                    ft.Text(f"Diferença: {brl(comparison['difference'])}",weight=ft.FontWeight.BOLD),
                    ft.Text(f"Cashback recebido: {brl(comparison['cashback'])}"),
                    ft.Text(f"Lançar despesa de {brl(comparison['receipt'])} em {selected_date} no perfil selecionado." if should_post else "Somente conferir a compra; nenhuma despesa será criada."),
                    ft.Text("Revise divergências antes de confirmar. As fotos são temporárias e serão descartadas ao fechar esta conferência.",size=11),
                ]))
                committing=False
                completed=False
                def commit(e):
                    nonlocal committing,completed
                    if committing or completed:return
                    committing=True
                    try:
                        current=receipt_comparison(self.cloud.list_market_items(trip["id"]),comparison['receipt'],comparison['cashback'])
                        if current != comparison:
                            self.page.pop_dialog()
                            self.snack("O carrinho mudou. Confira novamente antes de salvar.",True)
                            return
                        if str(self.active_member_id or '')!=member_id:
                            raise ValueError('O perfil mudou. Abra a conferência novamente.')
                        if should_post:
                            result=self.cloud.finalize_market_expense(trip['id'],comparison['cart'],comparison['receipt'],comparison['cashback'],member_id,selected_date)
                        else:
                            result=self.cloud.finish_market_trip(trip['id'],comparison['cart'],comparison['receipt'],comparison['cashback'])
                        completed=True
                        self.receipt_photos.clear()
                        self.page.pop_dialog()
                        self.page.pop_dialog()
                        self.render()
                        self.snack(("Compra e despesa confirmadas." if should_post else "Compra conferida.") if result.get('_sync_state')=='synced' else "Salvo no aparelho; aguardando sincronização. A nuvem ainda não confirmou.")
                    except Exception as exc:
                        self.snack(f"Não foi possível salvar a conferência: {exc}. Seus campos continuam abertos.",True)
                    finally:committing=False
                confirm.actions=[ft.TextButton("Voltar e corrigir",on_click=lambda e:self.page.pop_dialog()),ft.Button("Confirmar e salvar",on_click=commit)]
                self.page.show_dialog(confirm)
            except Exception as ex:self.snack(str(ex),True)
        def cancel(e):
            self.receipt_photos.clear()
            self.page.pop_dialog()
        d.actions=[ft.TextButton("Cancelar",on_click=cancel),ft.Button("Comparar valores",on_click=finish)]
        self.page.show_dialog(d)
