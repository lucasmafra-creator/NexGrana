from ui.common import AFFILIATE_DISCLOSURE, active_offers, brl, fc, ft, money
from services.market import product_values, receipt_comparison

class MarketScreen:
    RECEIPT_PHOTO_LIMIT = 6
    RECEIPT_TOTAL_BYTES_LIMIT = 18 * 1024 * 1024

    def _open_offer(self, offer, origin="market"):
        """Registra somente metadados comerciais permitidos e abre o parceiro.

        Analytics remoto permanece desativado por padrão; nenhum valor financeiro,
        texto de compra ou identificador familiar entra no evento.
        """
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
        d=ft.AlertDialog(title=ft.Text("Editar compra"),content=ft.Column(tight=True,controls=[name,budget]))
        def save(e):
            try:
                self.cloud.update_market_trip(trip["id"],market_name=name.value.strip(),budget=money(budget.value or 0))
                self.page.pop_dialog();self.render()
            except Exception as ex:self.snack(str(ex),True)
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
        trips=self.cloud.list_market_trips()
        active=next((x for x in trips if x.get("status")=="open"),None)
        controls=[]
        if active:
            items=self.cloud.list_market_items(active["id"])
            total=sum(float(x.get("unit_price") or 0)*float(x.get("quantity") or 0) for x in items)
            budget=float(active.get("budget") or 0)
            item_rows=[]
            for x in items[-40:]:
                item_rows.append(ft.Container(
                    padding=10,border_radius=12,bgcolor=self.surface_alt_color(),
                    content=ft.Row(controls=[
                        ft.Icon(ft.Icons.SHOPPING_BASKET_OUTLINED,color="#8B7CFF"),
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
                            ft.Text(f"{len(items)} tipo(s) • {sum(float(x.get('quantity') or 0) for x in items):g} unidade(s) • Carrinho {brl(total)}" + (f" • Restante {brl(budget-total)}" if budget else ""),size=11,color=self.muted_color()),
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
                ft.Container(col={"xs":4,"sm":2},alignment=ft.Alignment.CENTER,content=ft.Image(src=self.nex_asset("thinking","card"),width=115,height=115,fit=ft.BoxFit.CONTAIN)),
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

        # Monetização opcional e transparente. Ofertas nunca alteram os cálculos
        # nem são priorizadas pelo motor financeiro do Nex.
        offers=active_offers(self.cloud.list_affiliate_offers())
        if offers:
            offer_cards=[]
            for o in offers[:6]:
                offer_cards.append(ft.Container(
                    padding=12,border_radius=14,bgcolor=self.surface_alt_color(),
                    border=ft.Border.all(1,self.border_color()),
                    content=ft.Row(vertical_alignment=ft.CrossAxisAlignment.CENTER,controls=[
                        ft.Icon(ft.Icons.LOCAL_OFFER_OUTLINED,color="#8B7CFF"),
                        ft.Column(expand=True,spacing=2,controls=[
                            ft.Text(o.get("title") or "Oferta",weight=ft.FontWeight.BOLD),
                            ft.Text(o.get("subtitle") or "",size=9,color=self.muted_color()),
                            ft.Text(f"{o.get('provider','Parceiro')} • {o.get('badge','Link externo')}",size=8,color="#8B7CFF"),
                        ]),
                        ft.Button("Ver oferta",icon=ft.Icons.OPEN_IN_NEW,on_click=lambda e,row=o:self._open_offer(row,"market")),
                    ])
                ))
            controls.append(ft.Container(
                padding=15,bgcolor=self.surface_color(),border_radius=18,border=ft.Border.all(1,"#3B3566"),
                content=ft.Column(spacing=9,controls=[
                    ft.Row(controls=[ft.Icon(ft.Icons.SAVINGS_OUTLINED,color="#8B7CFF"),ft.Text("Achados Nex — ofertas opcionais",size=17,weight=ft.FontWeight.BOLD)]),
                    ft.Text(AFFILIATE_DISCLOSURE,size=9,color=self.muted_color()),
                    *offer_cards,
                ])
            ))
        return ft.Column(expand=True,controls=[
            self.header("Mercado","Carrinho, conferência da nota e histórico de preços"),
            ft.Container(padding=16,expand=True,content=ft.Column(scroll=ft.ScrollMode.ALWAYS,spacing=12,controls=controls))
        ])


    def _delete_market_item(self, rid):
        try:
            self.cloud.delete_market_item(rid);self.render()
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
        qty=ft.TextField(label="Quantidade",value="1",keyboard_type=ft.KeyboardType.NUMBER,col={"xs":12,"sm":6})
        price=ft.TextField(label="Preço unitário",keyboard_type=ft.KeyboardType.NUMBER,col={"xs":12,"sm":6})
        category=ft.Dropdown(label="Categoria",value="Alimentação",options=[ft.DropdownOption(x) for x in ["Alimentação","Carnes","Higiene","Limpeza","Bebidas","Doces/snacks","Pet","Casa","Outros"]])
        hint=ft.Text("No celular, os campos se reorganizam automaticamente. Reconhecimento por foto/código de barras será ativado quando houver um motor confiável; o app não adivinha produtos.",size=10,color=self.muted_color())
        d=ft.AlertDialog(title=ft.Text("Adicionar produto"),content=ft.Column(width=520,tight=True,controls=[product,ft.ResponsiveRow(controls=[qty,price]),category,hint]))
        def save(e, keep=False):
            if not product.value.strip(): self.snack("Informe o produto.",True); return
            try:
                name, q, v = product_values(product.value, qty.value or '1', money(price.value))
                self.cloud.add_market_item(trip['id'],name,float(q),float(v),category.value)
                if keep:
                    product.value=""; qty.value="1"; price.value=""; product.focus(); self.page.update()
                    self.snack("Produto adicionado. Continue a compra.")
                else:
                    self.page.pop_dialog(); self.render()
            except Exception as ex:self.snack(str(ex),True)
        d.actions=[ft.TextButton("Cancelar",on_click=lambda e:self.page.pop_dialog()),ft.OutlinedButton("Adicionar e continuar",on_click=lambda e:save(e,True)),ft.Button("Adicionar",on_click=lambda e:save(e,False))]
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
        self.receipt_photos = []
        items=self.cloud.list_market_items(trip["id"])
        cart=sum(float(x.get("unit_price") or 0)*float(x.get("quantity") or 0) for x in items)
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
                photo_status,thumbs,help_box,receipt,cashback,cashback_help,
                ft.TextButton("Ver opções de cashback no Méliuz",icon=ft.Icons.OPEN_IN_NEW,on_click=lambda e:self.page.run_task(self.open_external_url,"https://www.meliuz.com.br/"))
            ])
        )
        def finish(e):
            try:
                if not str(receipt.value or '').strip():
                    raise ValueError("Informe o total da nota")
                comparison=receipt_comparison(self.cloud.list_market_items(trip["id"]),money(receipt.value),money(cashback.value or 0))
                confirm=ft.AlertDialog(title=ft.Text("Confirmar valores conferidos"),content=ft.Column(tight=True,controls=[
                    ft.Text(f"Carrinho: {brl(comparison['cart'])}"),
                    ft.Text(f"Nota: {brl(comparison['receipt'])}"),
                    ft.Text(f"Diferença: {brl(comparison['difference'])}",weight=ft.FontWeight.BOLD),
                    ft.Text(f"Cashback recebido: {brl(comparison['cashback'])}"),
                    ft.Text("Revise divergências antes de confirmar. As fotos são temporárias e serão descartadas ao fechar esta conferência.",size=11),
                ]))
                def commit(e):
                    try:
                        current=receipt_comparison(self.cloud.list_market_items(trip["id"]),comparison['receipt'],comparison['cashback'])
                        if current != comparison:
                            self.page.pop_dialog()
                            self.snack("O carrinho mudou. Confira novamente antes de salvar.",True)
                            return
                        self.cloud.finish_market_trip(trip["id"],float(comparison['cart']),float(comparison['receipt']),float(comparison['cashback']))
                        self.receipt_photos.clear()
                        self.page.pop_dialog()
                        self.page.pop_dialog()
                        self.render()
                        self.snack("Compra conferida e salva.")
                    except Exception:
                        self.snack("Não foi possível salvar a conferência. Seus campos continuam abertos.",True)
                confirm.actions=[ft.TextButton("Voltar e corrigir",on_click=lambda e:self.page.pop_dialog()),ft.Button("Confirmar e salvar",on_click=commit)]
                self.page.show_dialog(confirm)
            except Exception as ex:self.snack(str(ex),True)
        def cancel(e):
            self.receipt_photos.clear()
            self.page.pop_dialog()
        d.actions=[ft.TextButton("Cancelar",on_click=cancel),ft.Button("Comparar valores",on_click=finish)]
        self.page.show_dialog(d)


