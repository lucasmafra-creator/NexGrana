from datetime import date, timedelta
from services.tutorial import MODULE_BY_KEY, TUTORIAL_MODULES, TutorialScope, TutorialSession, TutorialStatus, tutorial_financial_preview, training_money
from services.tutorial_activities import practice_basket, practice_investment, practice_income, practice_goal
from services.offers import DEMO_OFFERS
from ui.common import brl, day, ft, money


class TutorialScreen:
    """Tutorial guiado e interativo, isolado dos dados reais."""

    _TUTORIAL_ICONS={
        "welcome":ft.Icons.WAVING_HAND_OUTLINED,"balance":ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
        "income":ft.Icons.PAYMENTS_OUTLINED,"expense":ft.Icons.RECEIPT_LONG_OUTLINED,
        "acquisition":ft.Icons.DIRECTIONS_CAR_OUTLINED,"goals":ft.Icons.TRACK_CHANGES_OUTLINED,
        "investments":ft.Icons.SHOW_CHART,"extra_income":ft.Icons.LIGHTBULB_OUTLINE,
        "market":ft.Icons.SHOPPING_CART_OUTLINED,"offers":ft.Icons.LOCAL_OFFER_OUTLINED,
        "nex":ft.Icons.AUTO_AWESOME_OUTLINED,"family":ft.Icons.GROUP_OUTLINED,
        "privacy":ft.Icons.PRIVACY_TIP_OUTLINED,
    }

    def _tutorial_scope(self):
        return TutorialScope(
            user_id=str(getattr(getattr(self.cloud,"user",None),"id","")),
            household_id=str((getattr(self.cloud,"household",None) or {}).get("id") or ""),
            member_id=str(self.active_member_id or ""),
            session_generation=0,  # token refresh does not replace the tutorial owner
        )

    def tutorial_session(self):
        scope=self._tutorial_scope()
        current=getattr(self,"_tutorial_session_state",None)
        if current is None or current.scope.key != scope.key:
            saved=self.preferences.get(f"tutorial_progress_v2:{scope.user_id}:{scope.household_id}:{scope.member_id}")
            if not saved:
                saved=self.preferences.get(f"tutorial_progress_v2:{scope.member_id}") or {}
            current=TutorialSession.from_mapping(scope,saved)
            self._tutorial_session_state=current
        return current

    def _save_tutorial_progress(self):
        session=self.tutorial_session()
        self.preferences[f"tutorial_progress_v2:{session.scope.user_id}:{session.scope.household_id}:{session.scope.member_id}"]=session.to_mapping()
        self.save_preferences()

    def _refresh_tutorial_advance(self, key):
        button=getattr(self,"_tutorial_advance_button",None)
        if button is None or self.tutorial_session().current_module!=key:return
        button.content="Concluir tutorial" if key==TUTORIAL_MODULES[-1].key else "Próxima atividade"
        try:button.update()
        except Exception:pass

    def _module_index(self,key):
        return next((i for i,m in enumerate(TUTORIAL_MODULES) if m.key==key),0)

    def _select_tutorial_module(self,key):
        self.tutorial_session().start(key)
        self._save_tutorial_progress()
        self.render()

    def _next_tutorial_module(self,complete_current=True):
        session=self.tutorial_session()
        idx=self._module_index(session.current_module)
        if complete_current and session.current_module == "welcome":
            session.complete("welcome")
        elif complete_current and session.current_module not in session.statuses:
            session.skip(session.current_module)
        if idx >= len(TUTORIAL_MODULES)-1:
            self._save_tutorial_progress()
            self._finish_tutorial_dialog(completed=True)
            return
        session.start(TUTORIAL_MODULES[idx+1].key)
        self._save_tutorial_progress()
        self.render()

    def _previous_tutorial_module(self):
        session=self.tutorial_session()
        idx=self._module_index(session.current_module)
        if idx<=0:return
        session.start(TUTORIAL_MODULES[idx-1].key)
        self._save_tutorial_progress()
        self.render()

    def _eligible_tutorial_records(self,session):
        records=[]
        labels={"income":"Renda","expense":"Despesa","acquisition":"Aquisição","goals":"Meta"}
        required={
            "income":("origem","valor","data"),"expense":("descricao","valor","vencimento"),
            "acquisition":("item","valor","prioridade"),"goals":("meta","alvo","prazo"),
        }
        for key,fields in required.items():
            if session.statuses.get(key) in {TutorialStatus.SAVED.value,TutorialStatus.PENDING_SYNC.value}:
                continue  # never promote the same practiced record twice
            values=dict(session.sandbox.get(key) or {})
            if all(str(values.get(field) or "").strip() for field in fields):
                records.append((key,labels[key],values))
        return records

    def _commit_tutorial_records(self,session,records):
        member_id=str(self.active_member_id or (self.active_member() or {}).get("id") or "")
        if not member_id:
            raise ValueError("Selecione um perfil antes de salvar os exemplos.")
        results=[]
        priority_map={"alta":"Alta","media":"Média","média":"Média","baixa":"Baixa"}
        for key,_,values in records:
            stable=session.stable_commit_id(key)
            if key=="income":
                received=day(values["data"])
                result=self.cloud.add_income(member_id,money(values["valor"]),received.strftime("%m/%Y"),values["origem"],received_at=received.isoformat(),row_id=stable,operation_id=stable)
            elif key=="expense":
                due=day(values["vencimento"]); value=money(values["valor"])
                result=self.cloud.add_expense(member_id,"Variável","Outros",values["descricao"],value,due.isoformat(),due.strftime("%m/%Y"),shares=[(member_id,value)],row_id=stable,operation_id=stable)
            elif key=="acquisition":
                priority=priority_map.get(str(values["prioridade"]).strip().casefold())
                if not priority: raise ValueError("Use prioridade Alta, Média ou Baixa na aquisição.")
                result=self.cloud.add_acquisition(member_id,values["item"],priority,money(values["valor"]),0,"Criada pelo tutorial",row_id=stable,operation_id=stable)
            else:
                target=day(values["prazo"])
                result=self.cloud.add_goal(values["meta"],money(values["alvo"]),0,target.isoformat(),"Equilibrada",member_id=member_id,row_id=stable,operation_id=stable)
            pending=str((result or {}).get("_sync_state") or "")!="synced"
            session.complete(key,saved=not pending,pending_sync=pending)
            results.append(result)
        return results

    def _finish_tutorial_dialog(self,completed=False):
        session=self.tutorial_session()
        records=self._eligible_tutorial_records(session)
        selections={key:ft.Checkbox(value=False,label=f"{label}: {values.get('valor') or values.get('alvo') or 'ver detalhes'}")
                    for key,label,values in records}
        width,height=self.dialog_dimensions(560,500)
        def finish(action):
            if action=="discard":
                session.sandbox.clear()
                session.commit_ids.clear()
            elif action=="save":
                chosen=[row for row in records if selections[row[0]].value]
                if not chosen:
                    self.snack("Escolha explicitamente os registros que quer criar na conta.",True)
                    return
                try:
                    results=self._commit_tutorial_records(session,chosen)
                except Exception as exc:
                    self._save_tutorial_progress()  # retain receipts from earlier successful records
                    self.snack(f"Não foi possível salvar os registros: {exc}",True)
                    return
            for module in TUTORIAL_MODULES:
                if session.statuses.get(module.key) not in {TutorialStatus.COMPLETED.value,TutorialStatus.SAVED.value,TutorialStatus.PENDING_SYNC.value}:
                    session.statuses[module.key]=TutorialStatus.SKIPPED.value
            self.preferences["tutorial_offer_choice"]="accepted" if completed else "explore"
            self._save_tutorial_progress()
            self.page.pop_dialog()
            if action=="save":
                pending=any(str((row or {}).get("_sync_state") or "")!="synced" for row in results)
                self.snack("Registros salvos no aparelho e aguardando sincronização." if pending else "Registros confirmados e salvos na sua conta.")
            elif action=="discard":
                self.snack("Dados de treino descartados. Nenhum registro real foi criado.")
            else:
                self.snack("Treino mantido somente no tutorial; nenhum registro real foi criado.")
            self._go_screen(0)
        self.page.show_dialog(ft.AlertDialog(
            modal=True,
            title=ft.Text("Concluir tutorial" if completed else "Pular tutorial completo?"),
            content=ft.Column(width=width,height=height,tight=True,scroll=ft.ScrollMode.AUTO,controls=[
                ft.Text("Escolha claramente o que fazer com as informações digitadas no modo de treino."),
                ft.Container(padding=12,border_radius=12,bgcolor=self.surface_alt_color(),content=ft.Text(
                    ("Prontos para confirmação: "+", ".join(label for _,label,_ in records)+". Ao salvar, esses registros entram na sua conta." if records else "Nenhum exemplo completo está pronto para virar registro real.")
                )),
                ft.Text("Saldo hipotético e simulações de investimento nunca viram lançamentos reais.",size=10,color=self.muted_color()),
                ft.Text("Selecione apenas o que você quer registrar de verdade. Nenhum item vem marcado.",weight=ft.FontWeight.BOLD),
                *list(selections.values()),
            ]),
            actions=[
                ft.TextButton("Continuar tutorial",on_click=lambda _:self.page.pop_dialog()),
                ft.OutlinedButton("Descartar e sair",on_click=lambda _:finish("discard")),
                ft.TextButton("Manter só no treino",on_click=lambda _:finish("keep")),
                ft.Button("Salvar registros na conta",disabled=not records,on_click=lambda _:finish("save")),
            ],
        ))

    def _skip_entire_tutorial(self,e=None):
        self._finish_tutorial_dialog(completed=False)

    def _tutorial_balance_activity(self,session):
        def example(title,detail):
            return ft.Container(padding=13,bgcolor=self.surface_alt_color(),border_radius=12,
                content=ft.Column(spacing=4,controls=[ft.Text(title,weight=ft.FontWeight.BOLD),ft.Text(detail,size=12)]))
        return ft.Column(spacing=10,controls=[
            ft.Text("Como o saldo funciona",size=18,weight=ft.FontWeight.BOLD),
            ft.Text("Saldo atual considera a renda recebida e as despesas cujo vencimento chegou. Saldo projetado também mostra o impacto dos compromissos futuros."),
            example("Hoje", "Exemplo ilustrativo: R$ 200 disponíveis; uma conta de R$ 10 vence amanhã. Saldo atual: R$ 200; após o vencimento: R$ 190."),
            example("No vencimento", "A conta de R$ 10 passa a reduzir o saldo atual. Marcar uma conta como paga antes da data não antecipa o débito."),
            ft.Text("Nenhum valor deste exemplo é salvo na sua conta. Renda, despesa, aquisição e meta têm regras próprias.",size=11,color=self.muted_color()),
        ])

    def _tutorial_standard_activity(self,module,session):
        schemas={
            "income":[("origem","Origem da renda","Ex.: salário"),("valor","Valor recebido","Ex.: 2500,00"),("data","Data de recebimento","dd/mm/aaaa")],
            "expense":[("descricao","Descrição da despesa","Ex.: internet"),("valor","Valor","Ex.: 99,90"),("vencimento","Vencimento","dd/mm/aaaa")],
            "acquisition":[("item","Aquisição desejada","Ex.: notebook"),("valor","Custo estimado","Ex.: 4500,00"),("prioridade","Prioridade","Alta, média ou baixa")],
            "goals":[("meta","Nome da meta","Ex.: reserva"),("alvo","Valor alvo","Ex.: 5000,00"),("prazo","Prazo","dd/mm/aaaa")],
        }
        stored=dict(session.sandbox.get(module.key) or {})
        fields=[]
        for key,label,hint in schemas.get(module.key,[]):
            fields.append((key,ft.TextField(label=label,hint_text=hint,value=str(stored.get(key) or ""))))
        note=ft.Text("",size=11,color=ft.Colors.GREEN_400)
        illustration=ft.Text("Preencha os campos para visualizar um exemplo. Tudo continua no treino.",size=13)
        def describe(values):
            if module.key=="income":
                row=practice_income(values["origem"],values["valor"],values["data"])
                return f"+ {brl(row['amount'])} recebidos na competência {row['competence']}. Só entraria no saldo real após confirmar o registro."
            if module.key=="expense":
                cost=training_money(values["valor"])
                if not values["descricao"].strip() or cost <= 0:raise ValueError("Informe descrição e valor positivo")
                preview=tutorial_financial_preview(200,cost,values["vencimento"],date.today())
                return (f"Saldo de treino hoje: {brl(preview['current_balance'])} · Após o vencimento: {brl(preview['projected_balance'])}. "
                        "Conta futura ainda não debitada." if preview['pending'] else
                        f"Vencimento alcançado: saldo de treino {brl(preview['current_balance'])}.")
            if module.key=="acquisition":
                cost=training_money(values["valor"])
                if not values["item"].strip() or cost <= 0 or values["prioridade"].strip().casefold() not in ("alta","media","média","baixa"):
                    raise ValueError("Informe item, custo positivo e prioridade Alta, Média ou Baixa")
                return f"{values['item']}: intenção de compra de {brl(cost)} · prioridade {values['prioridade']}. Planejar não debita saldo."
            if module.key=="goals":
                if not values["meta"].strip():raise ValueError("Dê um nome à meta")
                target=day(values["prazo"])
                months=max(1,(target.year-date.today().year)*12+target.month-date.today().month+1)
                if target < date.today():raise ValueError("Escolha um prazo futuro")
                row=practice_goal(values["alvo"],"0",months)
                return f"Meta {values['meta']}: {brl(row['remaining'])} até o prazo · esforço de treino {brl(row['monthly'])}/mês. Nada reservado de verdade."
            return module.summary
        def preview(e=None):
            values={key:field.value or "" for key,field in fields}
            try:
                illustration.value=describe(values)
                illustration.color=ft.Colors.GREEN_400
            except (ValueError,TypeError) as exc:
                illustration.value=f"Revise os dados para ver o efeito: {exc}"
                illustration.color=self.muted_color()
            if e is not None:
                try:illustration.update()
                except Exception:pass
        for _,field in fields:
            field.on_change=preview
        preview()
        def save_training(e=None):
            values={key:field.value or "" for key,field in fields}
            try:describe(values)
            except (ValueError,TypeError) as exc:
                note.value=f"Confira os campos: {exc}";note.color=ft.Colors.RED_400;note.update();return
            session.sandbox[module.key]=values
            session.complete(module.key)
            self._save_tutorial_progress()
            self._refresh_tutorial_advance(module.key)
            note.value="Prática concluída somente no treino. Nenhum dado real foi criado."
            note.color=ft.Colors.GREEN_400
            note.update()
        controls=[
            ft.Container(padding=14,border_radius=16,bgcolor=self.surface_alt_color(),content=ft.Column(spacing=6,controls=[
                ft.Row(controls=[ft.Icon(self._TUTORIAL_ICONS[module.key],color="#8B7CFF"),ft.Text("Objetivo",weight=ft.FontWeight.BOLD)]),
                ft.Text(module.summary),ft.Text(module.task,size=11,color=self.muted_color()),
                ft.Text("MODO TREINO · Nenhum dado desta etapa entra na sua conta sem confirmação.",size=10,color="#8B7CFF"),
            ])),
        ]
        if fields:
            controls.append(ft.ResponsiveRow(controls=[ft.Container(col={"xs":12,"md":6},content=field) for _,field in fields]))
            controls.extend([ft.Container(padding=14,bgcolor=self.surface_alt_color(),border_radius=12,content=illustration),
                             ft.Button("Concluir prática no treino",icon=ft.Icons.SCIENCE_OUTLINED,on_click=save_training),note])
        else:
            controls.append(ft.Container(padding=14,border_radius=16,border=ft.Border.all(1,self.border_color()),content=ft.Text("Este passo apresenta as regras do app. Toque em Próximo passo quando estiver pronto.")))
        return ft.Column(spacing=12,controls=controls)

    def _tutorial_interactive_activity(self,module,session):
        """Distinct practice surfaces; every action stays in the isolated sandbox."""
        key=module.key
        stored=dict(session.sandbox.get(key) or {})
        caption=ft.Text("Treino: nada nesta atividade altera seus dados reais.",size=11,color="#8B7CFF")
        result=ft.Column(spacing=8)
        def record(values, message):
            session.sandbox[key]=values
            session.complete(key)
            self._save_tutorial_progress()
            self._refresh_tutorial_advance(key)
            result.controls=[ft.Text(message,color=ft.Colors.GREEN_400)]
            result.update()

        if key=="welcome":
            return ft.Column(spacing=14,controls=[
                ft.Text("Aqui você pode experimentar antes de registrar algo de verdade.",size=18,weight=ft.FontWeight.BOLD),
                ft.Text("Renda é dinheiro recebido; uma conta futura só reduz o saldo no vencimento. Aquisições e metas ajudam a planejar sem movimentar dinheiro."),
            ft.Text("Escolha qualquer atividade no menu ou comece registrando uma renda de treino. Você pode sair e voltar depois."),caption,
            ])
        if key=="investments":
            initial=ft.TextField(label="Valor inicial (R$)",value=str(stored.get("initial","1000")))
            monthly=ft.TextField(label="Aporte mensal (R$)",value=str(stored.get("monthly","200")))
            months=ft.TextField(label="Meses",value=str(stored.get("months","12")))
            rate=ft.TextField(label="Taxa anual hipotética (%)",value=str(stored.get("rate","0")))
            def simulate(_):
                try:
                    projection=practice_investment(initial.value,monthly.value,months.value,rate.value)
                    record({"initial":initial.value,"monthly":monthly.value,"months":months.value,"rate":rate.value},
                           f"Aportes: {brl(projection['total_invested'])} · Resultado simulado: {brl(projection['net_result'])}. Não há garantia de retorno.")
                except ValueError as exc:
                    result.controls=[ft.Text(str(exc),color=ft.Colors.RED_400)];result.update()
            return ft.Column(spacing=12,controls=[
                ft.Text("Simule cenários: mudar o prazo ou a taxa altera o resultado; a taxa é uma hipótese sua."),
                ft.ResponsiveRow(controls=[ft.Container(col={"xs":12,"md":6},content=field) for field in (initial,monthly,months,rate)]),
                ft.Button("Projetar investimento",on_click=simulate),caption,result])
        if key=="extra_income":
            options=("Freelance","Serviço local","Venda","Aulas")
            available=ft.Dropdown(label="Horas por semana",value=str(stored.get("hours","4")),
                                  options=[ft.DropdownOption(value) for value in ("2","4","8","12")])
            note=ft.Text("Escolha uma ideia para descobrir o primeiro passo.")
            def choose(choice):
                record({"idea":choice,"hours":available.value},
                       f"Primeira missão: converse com três possíveis clientes sobre {choice.lower()}. Registre custos e horas antes de definir preço. Sem promessa de ganhos.")
            return ft.Column(spacing=12,controls=[ft.Text("Renda extra é uma atividade sua. Os links de Achados financiam o app e não entram aqui."),
                available,ft.Row(wrap=True,controls=[ft.OutlinedButton(option,on_click=lambda _,name=option:choose(name)) for option in options]),note,caption,result])
        if key=="market":
            items=list(stored.get("items") or [])
            budget=ft.TextField(label="Orçamento do treino",value=str(stored.get("budget","900")))
            name=ft.TextField(label="Produto",hint_text="Ex.: arroz")
            qty=ft.TextField(label="Quantidade",value="1")
            price=ft.TextField(label="Preço por unidade (R$)",hint_text="Ex.: 24,90")
            cart=ft.Column(spacing=4)
            def paint():
                try:
                    summary=practice_basket(items,budget.value)
                    total=f"Carrinho: {brl(summary['total'])} · Restante: {brl(summary['remaining'])}"
                    if summary["over_budget"]: total+=" · Acima do orçamento"
                except ValueError as exc:total=f"Revise o orçamento: {exc}"
                cart.controls=[ft.Text(total,weight=ft.FontWeight.BOLD)]+[
                    ft.Row(wrap=True,controls=[ft.Text(f"{row['name']} · {row['quantity']} × {row['price']}"),
                        ft.TextButton("Remover",on_click=lambda _,index=i:remove(index))]) for i,row in enumerate(items)]
                try:cart.update()
                except Exception:pass
            def remove(index):
                items.pop(index)
                session.sandbox[key]={"items":items,"budget":budget.value}
                self._save_tutorial_progress();paint()
            def add(_):
                try:
                    number=int(qty.value)
                    row={"name":name.value.strip(),"quantity":number,"price":price.value}
                    practice_basket(items+[row],budget.value)
                    items.append(row)
                    session.sandbox[key]={"items":items,"budget":budget.value}
                    session.complete(key);self._save_tutorial_progress();self._refresh_tutorial_advance(key);paint()
                    name.value="";price.value="";name.update();price.update()
                except (ValueError,TypeError) as exc:
                    result.controls=[ft.Text(f"Revise o item: {exc}",color=ft.Colors.RED_400)];result.update()
            paint()
            return ft.Column(spacing=12,controls=[ft.Text("Monte uma lista curta. O orçamento e o total mudam quando você adiciona ou remove itens."),
                budget,ft.ResponsiveRow(controls=[ft.Container(col={"xs":12,"md":4},content=field) for field in (name,qty,price)]),
                ft.Button("Adicionar ao carrinho de treino",on_click=add),cart,caption,result])
        if key=="offers":
            query=ft.TextField(label="Buscar Achados",hint_text="Ex.: cafeteira",value=str(stored.get("query", "")))
            results=ft.Column(spacing=7)
            def search(_=None):
                text=(query.value or "").strip().casefold()
                rows=[offer for offer in DEMO_OFFERS if text in (offer["title"]+" "+offer["category"]).casefold()]
                results.controls=[ft.Text(f"{len(rows)} produto(s) encontrado(s). Compare o preço e as condições no parceiro.")]+[
                    ft.Container(padding=8,bgcolor=self.surface_alt_color(),content=ft.Text(offer["title"]+" · "+offer["category"])) for offer in rows]
                session.sandbox[key]={"query":query.value};session.complete(key);self._save_tutorial_progress();self._refresh_tutorial_advance(key)
                results.update()
            query.on_change=search
            return ft.Column(spacing=12,controls=[ft.Text("Achados mostra links externos de afiliados. Mercado serve para controlar suas compras. Buscar aqui não registra uma compra."),
                query,caption,results])
        if key=="nex":
            question=ft.TextField(label="Fale com o Nex no treino",hint_text="Ex.: opa bro",value="")
            messages=list(stored.get("messages") or [])[-8:]
            if not messages:
                messages=[{"role":"assistant","text":"Oi! Pode conversar comigo sobre o app. Aqui é um treino local e não leio seu extrato."}]
            conversation=ft.Column(spacing=6,scroll=ft.ScrollMode.AUTO,controls=[])
            def paint():
                conversation.controls=[ft.Container(padding=9,border_radius=11,
                    bgcolor=self.user_bubble_color() if row["role"]=="user" else self.assistant_bubble_color(),
                    content=ft.Text(("Você: " if row["role"]=="user" else "Nex: ")+row["text"])) for row in messages]
                try:conversation.update()
                except Exception:pass
            paint()
            def talk(_=None):
                text=(question.value or "").strip()
                if not text:return
                lowered=text.casefold()
                if any(x in lowered for x in ("oi","opa","salve","eae","bro")):
                    answer="Opa! Pode perguntar como funciona renda, despesa ou a conversa no app."
                elif any(x in lowered for x in ("despesa","conta","pagar")):
                    answer="Uma despesa futura aparece no projetado; no saldo atual, ela só entra quando chega o vencimento. Quer falar de outra parte?"
                elif any(x in lowered for x in ("renda","salário","salario")):
                    answer="Renda recebida soma ao mês correspondente. Aqui não mexemos no seu saldo real. O que mais você quer aprender?"
                else:
                    answer="Entendi. Neste treino minhas respostas são locais. Continue perguntando; no chat principal você pode seguir a conversa e consultar seu próprio perfil."
                messages.extend([{"role":"user","text":text[:300]},{"role":"assistant","text":answer}])
                del messages[:-10]
                session.sandbox[key]={"messages":list(messages)};session.complete(key);self._save_tutorial_progress();self._refresh_tutorial_advance(key)
                paint();question.value="";question.update()
            question.on_submit=talk
            return ft.Column(spacing=12,controls=[ft.Text("Conversa de demonstração, separada do seu histórico e sem usar IA externa."),
                conversation,question,ft.Button("Enviar ao Nex de treino",on_click=talk),caption])
        if key=="family":
            chosen=ft.Text("Selecione uma visão para entender quem aparece em cada total.")
            def view(scope):
                record({"view":scope},"Visão pessoal: só dados do seu perfil." if scope=="Pessoal" else
                       "Visão da família: soma autorizada dos integrantes; a conta compartilhada entra uma vez no total.")
                chosen.value=scope+" · exemplo fictício, sem criar integrantes";chosen.update()
            return ft.Column(spacing=12,controls=[ft.Text("Cada pessoa tem seu perfil; você escolhe ver apenas o seu ou o total compartilhado conforme suas permissões."),
                ft.Row(wrap=True,controls=[ft.OutlinedButton("Meu perfil",on_click=lambda _:view("Pessoal")),
                                            ft.OutlinedButton("Consolidado",on_click=lambda _:view("Família"))]),chosen,caption,result])
        if key=="privacy":
            options=[
                ("external_ai","Nex online","Envia sua pergunta e o contexto recente somente depois da autorização real."),
                ("reminders","Lembretes","Mostra lembretes opcionais das atividades do app."),
                ("affiliate_personalization","Achados personalizados","Usa preferências explícitas para organizar os links de Achados."),
            ]
            choices={purpose:ft.Checkbox(value=bool(stored.get(purpose,False)),label=title)
                     for purpose,title,_ in options}
            def practice(_):
                values={purpose:bool(choice.value) for purpose,choice in choices.items()}
                record(values,"Escolhas guardadas só no treino. Para aplicar de verdade, abra Configurações → Privacidade e exportação.")
            cards=[ft.Container(border_radius=12,padding=12,bgcolor=self.surface_alt_color(),
                    content=ft.Column(spacing=2,controls=[choices[purpose],
                        ft.Text(description,size=11,color=self.muted_color())]))
                   for purpose,_,description in options]
            return ft.Column(spacing=12,controls=[ft.Text("Experimente as escolhas. Esta simulação não autoriza a IA nem altera sua conta."),
                *cards,ft.Button("Guardar escolhas no treino",on_click=practice),caption,result])
        return self._tutorial_standard_activity(module,session)

    def _navigation_controls(self,module):
        idx=self._module_index(module.key)
        last=idx==len(TUTORIAL_MODULES)-1
        session=self.tutorial_session()
        complete=session.statuses.get(module.key) in {TutorialStatus.COMPLETED.value,TutorialStatus.SAVED.value,TutorialStatus.PENDING_SYNC.value}
        explanatory=module.key in {"welcome","balance"}
        def advance(_):
            already_done=session.statuses.get(module.key) in {TutorialStatus.COMPLETED.value,TutorialStatus.SAVED.value,TutorialStatus.PENDING_SYNC.value}
            if not already_done and not explanatory:
                session.skip(module.key)
            self._next_tutorial_module(complete_current=explanatory and not already_done)
        button=ft.Button(("Concluir tutorial" if last else "Próxima atividade") if complete else
            ("Concluir esta atividade" if explanatory else "Pular esta atividade"),
            icon=ft.Icons.CHECK if last or explanatory else ft.Icons.CHEVRON_RIGHT,on_click=advance)
        self._tutorial_advance_button=button
        return ft.Container(
            padding=ft.Padding.symmetric(vertical=10),
            content=ft.Row(wrap=True,alignment=ft.MainAxisAlignment.SPACE_BETWEEN,controls=[
                ft.OutlinedButton("Passo anterior",icon=ft.Icons.CHEVRON_LEFT,disabled=idx==0,on_click=lambda _:self._previous_tutorial_module()),
            button,
            ]),
        )

    def tutorial_screen(self):
        session=self.tutorial_session(); module=MODULE_BY_KEY[session.current_module]
        phone=self._layout_bucket()=="phone"
        module_cards=[]
        for item in TUTORIAL_MODULES:
            status=session.statuses.get(item.key,TutorialStatus.NOT_STARTED.value)
            done=status in {TutorialStatus.COMPLETED.value,TutorialStatus.SAVED.value,TutorialStatus.PENDING_SYNC.value}
            module_cards.append(ft.Container(border_radius=12,bgcolor="#292654" if item.key==module.key else self.surface_alt_color(),content=ft.ListTile(
                leading=ft.Icon(ft.Icons.CHECK_CIRCLE if done else self._TUTORIAL_ICONS[item.key],color=ft.Colors.GREEN_400 if done else "#8B7CFF"),
                title=ft.Text(item.title,weight=ft.FontWeight.BOLD if item.key==module.key else None),subtitle=ft.Text("Concluído" if done else item.summary,max_lines=2,size=9),
                on_click=lambda e,key=item.key:self._select_tutorial_module(key))))
        activity=self._tutorial_balance_activity(session) if module.key=="balance" else self._tutorial_interactive_activity(module,session)
        header=ft.Container(padding=ft.Padding.symmetric(horizontal=12,vertical=8),bgcolor=self.surface_color(),content=ft.Row(controls=[
            ft.Column(expand=True,spacing=1,controls=[ft.Text("Aprender fazendo",size=20,weight=ft.FontWeight.BOLD),ft.Text(f"{session.completed_count}/{len(TUTORIAL_MODULES)} atividades concluídas",size=10,color=self.muted_color())]),
            ft.TextButton("Pular tutorial completo",icon=ft.Icons.SKIP_NEXT,on_click=self._skip_entire_tutorial),
        ]))
        progress=ft.ProgressBar(value=session.progress,color="#8B7CFF",bgcolor=self.surface_alt_color())
        hero=ft.Container(padding=12,border_radius=16,bgcolor=self.surface_alt_color(),content=ft.Row(controls=[
            ft.Image(src=self.nex_asset("study","card"),width=74 if phone else 92,height=74 if phone else 92,fit=ft.BoxFit.CONTAIN),
            ft.Column(expand=True,controls=[ft.Text(module.title,size=18 if phone else 24,weight=ft.FontWeight.BOLD),ft.Text("Treino interativo isolado dos seus dados reais.",size=10,color=self.muted_color())])]))
        if phone:
            body=ft.Column(expand=True,scroll=ft.ScrollMode.AUTO,controls=[
                ft.Dropdown(label="Atividade",value=module.key,options=[ft.DropdownOption(key=m.key,text=m.title) for m in TUTORIAL_MODULES],on_select=lambda e:self._select_tutorial_module(e.control.value)),
                hero,activity,self._navigation_controls(module)])
        else:
            body=ft.Row(expand=True,vertical_alignment=ft.CrossAxisAlignment.START,controls=[
                ft.Container(width=300,padding=8,content=ft.ListView(expand=True,spacing=6,controls=module_cards)),
                ft.VerticalDivider(width=1),
                ft.Container(expand=True,padding=18,content=ft.Column(expand=True,scroll=ft.ScrollMode.AUTO,controls=[hero,activity,self._navigation_controls(module)])),
            ])
        return ft.Column(expand=True,spacing=0,controls=[header,progress,ft.Container(expand=True,padding=12,content=body)])
