from ui.common import Context, EXTRA_INCOME_MANUALS, FINANCIAL_KNOWLEDGE, SequenceMatcher, add_months, brl, date, datetime, day, expense_status, ft, money, month_label, re, unicodedata, uuid, asyncio, logger

class NexScreen:
    def _nex_runtime(self):
        return getattr(self, "_nex_chat_runtime", None) or {}

    def _chat_bubble(self, msg, phone=None):
        phone = self._layout_bucket() == "phone" if phone is None else bool(phone)
        is_user = msg.get("role") == "user"
        if is_user:
            return ft.Container(
                padding=ft.Padding.only(top=2,bottom=4),
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.END,
                    controls=[ft.Container(
                        expand=True,
                        padding=11,
                        border_radius=16,
                        bgcolor="#2D3563",
                        content=ft.Text(msg.get("text") or "",size=12,selectable=True),
                    )],
                ),
            )
        return ft.Container(
            padding=ft.Padding.only(top=4,bottom=8),
            content=ft.Row(
                vertical_alignment=ft.CrossAxisAlignment.START,
                controls=[
                    ft.Image(src=self.nex_asset("idle","avatar"),width=48 if phone else 54,height=48 if phone else 54,fit=ft.BoxFit.CONTAIN,gapless_playback=True),
                    ft.Container(expand=True,padding=12,border_radius=16,bgcolor=self.assistant_bubble_color(),content=ft.Text(msg.get("text") or "",size=12,selectable=True)),
                ],
            ),
        )

    def _refresh_nex_runtime(self):
        """Atualiza somente o chat, sem remontar a tela inteira.

        Isso reduz o flicker observado no notebook e evita perder foco/IME no
        Android quando uma mensagem é enviada.
        """
        rt=self._nex_runtime()
        chat_list=rt.get("list")
        question=rt.get("question")
        send_button=rt.get("send")
        quick_buttons=rt.get("quick_buttons") or []
        if chat_list is None:
            return False
        phone=self._layout_bucket()=="phone"
        controls=[self._chat_bubble(m,phone) for m in self.chat_messages[-80:]]
        if self.nex_busy:
            controls.append(ft.Container(
                padding=ft.Padding.only(top=4,bottom=8),
                content=ft.Row(vertical_alignment=ft.CrossAxisAlignment.CENTER,controls=[
                    ft.Image(src=self.nex_asset("thinking","avatar"),width=42 if phone else 48,height=42 if phone else 48,fit=ft.BoxFit.CONTAIN),
                    ft.Container(padding=10,border_radius=16,bgcolor=self.assistant_bubble_color(),content=ft.Text("Nex está pensando…",size=11,italic=True,color=self.muted_color())),
                ]),
            ))
        chat_list.controls=controls
        if question is not None:
            question.disabled=self.nex_busy
        if send_button is not None:
            send_button.disabled=self.nex_busy
        for btn in quick_buttons:
            btn.disabled=self.nex_busy
        try:
            chat_list.update()
            if question is not None: question.update()
            if send_button is not None: send_button.update()
            for btn in quick_buttons: btn.update()
            return True
        except Exception:
            return False

    def _queue_nex_message(self, text, source="chat", entity_id=None, action=None, payload=None, question=None):
        """Entrada síncrona única usada por botão/submit/atalhos em todas as plataformas."""
        q=(text or "").strip()
        if not q:
            return False
        if self.nex_busy:
            self.snack("O Nex ainda está terminando a resposta anterior.")
            return False
        if question is not None:
            self.nex_draft=""
            try:
                question.value=""
                question.update()
            except Exception:
                pass
        self.page.run_task(self._dispatch_nex_message,q,source,entity_id,action,payload)
        return True

    async def _dispatch_nex_message(self, text, source="chat", entity_id=None, action=None, payload=None):
        q=(text or "").strip()
        if not q or self.nex_busy:
            return None
        request_id=str(uuid.uuid4())
        scope=(str(self.cloud._hid()),str(self.active_member_id or ""),self.month)
        self.nex_busy=True
        self.nex_draft=""
        self.chat_messages.append({"role":"user","text":q,"request_id":request_id})
        self.chat_messages=self.chat_messages[-120:]
        if not self._refresh_nex_runtime():
            try:
                self.render()
            except Exception:
                logger.warning("nex_render_before_dispatch_failed")
        try:
            await asyncio.sleep(0)
            context=Context(
                source=source,
                household_id=scope[0],
                member_id=scope[1],
                month=scope[2],
                entity_id=str(entity_id) if entity_id is not None else None,
                action=action,
                payload=payload or {},
                request_id=request_id,
                conversation_id=str(getattr(self,"conversation_id","") or "local"),
                snapshot_reference=f"{scope[0]}:{scope[1]}:{scope[2]}",
            )
            response=await asyncio.to_thread(self.nex_engine.respond,q,context)
            # Resposta tardia de outra conta/perfil/mês é descartada.
            current_scope=(str(self.cloud._hid()),str(self.active_member_id or ""),self.month)
            if current_scope != scope:
                logger.info("nex_stale_response_discarded")
                return None
            response=(response or "").strip() or "Não consegui montar uma resposta confiável agora. Não vou inventar dados; tente novamente."
            self.chat_messages.append({"role":"assistant","text":response,"request_id":request_id})
            self.chat_messages=self.chat_messages[-120:]
            try:
                self.analytics.track("nex_request_completed",source=source,result="success",latency_bucket="local")
            except Exception:
                pass
            return response
        except Exception as exc:
            logger.warning("nex_dispatch_failed kind=%s",type(exc).__name__)
            self.chat_messages.append({"role":"assistant","text":"Tive um problema ao processar isso agora. Nenhum valor foi inventado. Tente novamente.","request_id":request_id})
            self.chat_messages=self.chat_messages[-120:]
            return None
        finally:
            self.nex_busy=False
            if not self._refresh_nex_runtime():
                try:self.render()
                except Exception:logger.warning("nex_render_after_dispatch_failed")

    def _process_nex_message(self, text, source="chat", entity_id=None):
        return self._queue_nex_message(text,source,entity_id)

    def _start_nex_topic(self, text, source="action", entity_id=None, action=None, payload=None):
        try:self.page.pop_dialog()
        except (IndexError, AssertionError, AttributeError):pass
        self._go_nex_chat()
        self._queue_nex_message(text,source,entity_id,action,payload)

    def chat_screen(self):
        phone=self._layout_bucket()=="phone"
        if not self.chat_messages:
            hour=datetime.now().hour
            period="Bom dia" if hour<12 else ("Boa tarde" if hour<18 else "Boa noite")
            who=(self.active_member() or {}).get("display_name") or "por aí"
            self.chat_messages.append({"role":"assistant","text":f"{period}, {who}! 👋 Eu sou o Nex. Pode falar normal comigo. Quando eu usar números, eles vêm dos dados reais da família. 🦉"})

        chat_list=ft.ListView(expand=True,spacing=4,auto_scroll=True,scroll=ft.ScrollMode.ALWAYS,controls=[self._chat_bubble(m,phone) for m in self.chat_messages[-80:]])
        question=ft.TextField(
            value=self.nex_draft,
            hint_text="Fale com o Nex...",
            multiline=True,
            shift_enter=True,
            min_lines=1,
            max_lines=3 if phone else 4,
            expand=True,
            border_radius=16,
            disabled=self.nex_busy,
            text_size=16 if phone else 13,
        )
        mobile_focus_controls={}

        def _set_composer_focus(focused):
            self.nex_draft=(question.value or self.nex_draft or "") if not focused else self.nex_draft
            if not phone:return
            # O teclado Android compete com a NavigationBar. Durante digitação,
            # preservamos a área do composer e ocultamos conteúdo não essencial.
            if self.page.navigation_bar is not None:
                self.page.navigation_bar.visible=not focused
                try:self.page.navigation_bar.update()
                except Exception:pass
            for key in ("header","hero","quick","spacer"):
                ctrl=mobile_focus_controls.get(key)
                if ctrl is not None:
                    ctrl.visible=not focused
                    try:ctrl.update()
                    except Exception:pass

        def submit(e=None):
            self._queue_nex_message(question.value,"chat",None,"message",{},question=question)

        question.on_submit=submit
        question.on_focus=lambda e:_set_composer_focus(True)
        question.on_blur=lambda e:_set_composer_focus(False)

        def quick_handler(text,action):
            return lambda e:self._queue_nex_message(text,"quick",None,action,{})

        active_name=(self.active_member() or {}).get("display_name") or "a família"
        mood,_=self._nex_suggestion()
        hero=ft.Container(
            padding=12 if phone else 14,border_radius=18,bgcolor="#17192B" if self.is_dark() else "#F3F1FF",border=ft.Border.all(1,"#393266"),
            content=ft.ResponsiveRow(vertical_alignment=ft.CrossAxisAlignment.CENTER,controls=[
                ft.Container(col={"xs":3,"sm":3},alignment=ft.Alignment.CENTER,content=ft.Container(
                    width=72 if phone else 124,height=72 if phone else 124,on_click=lambda e:self.page.run_task(self.nex_click_and_chat),tooltip="Toque no Nex",
                    content=ft.Image(src=self.nex_asset(mood,"card"),width=72 if phone else 124,height=72 if phone else 124,fit=ft.BoxFit.CONTAIN,gapless_playback=True))),
                ft.Container(col={"xs":9,"sm":9},content=ft.Column(spacing=5,controls=[
                    ft.Text(f"Nex está com {active_name}",size=18,weight=ft.FontWeight.BOLD),
                    ft.Text("Consultas e simulações usam registros da família. Se faltar dado, eu aviso — não chuto valor.",size=10,color=self.muted_color()),
                    ft.Text("🦉 Toque no Nex para uma reação.",size=9,color="#8B7CFF",italic=True),
                ])),
            ]),
        )
        quick_specs=[
            ("Como está meu mês?","month_summary"),
            (("Qual aquisição faz sentido agora?" if self.cloud.list_acquisitions(True) else "Posso comprar algo agora?"),"evaluate_acquisition"),
            ("Me ajude a economizar","save_money"),
            ("Próximas contas","next_bills"),
        ]
        quick_buttons=[]
        for text,action in quick_specs:
            btn=ft.OutlinedButton(text,col={"xs":6,"md":3},disabled=self.nex_busy,on_click=quick_handler(text,action))
            quick_buttons.append(btn)
        quick=ft.ResponsiveRow(spacing=6,run_spacing=6,controls=quick_buttons)
        screen_header=self.header("Nex","Seu parceiro financeiro inteligente")
        hero_wrap=ft.Container(content=hero)
        hero_spacer=ft.Container(height=12 if phone else 4)
        quick_wrap=ft.Container(content=quick)
        mobile_focus_controls.update({"header":screen_header,"hero":hero_wrap,"quick":quick_wrap,"spacer":hero_spacer})
        send_button=ft.IconButton(ft.Icons.SEND_ROUNDED,tooltip="Enviar",disabled=self.nex_busy,on_click=submit)
        composer=ft.Container(
            padding=ft.Padding.only(top=8,bottom=18 if phone else 6),
            content=ft.Row(vertical_alignment=ft.CrossAxisAlignment.END,controls=[question,send_button]),
        )
        self._nex_chat_runtime={"list":chat_list,"question":question,"send":send_button,"quick_buttons":quick_buttons}
        if self.nex_busy:self._refresh_nex_runtime()
        return ft.Column(expand=True,spacing=0,controls=[
            screen_header,
            ft.Container(expand=True,padding=12 if phone else 16,content=ft.Column(expand=True,spacing=14 if phone else 12,controls=[
                hero_wrap,hero_spacer,chat_list,ft.Container(height=8 if phone else 0),quick_wrap,composer,
            ])),
        ])


    def _norm(self, text):
        text=unicodedata.normalize("NFKD", str(text or "")).encode("ascii","ignore").decode().lower()
        return re.sub(r"[^a-z0-9]+", " ", text).strip()


    def _simple_word(self, word):
        w=self._norm(word)
        if len(w)>4 and w.endswith("s"):
            w=w[:-1]
        return w


    def _expense_scope_from_question(self, q):
        # Default: mês selecionado. Reconhece apenas janelas explícitas; não presume período.
        qn=self._norm(q)
        months=[self.month]
        m=re.search(r"ultim(?:o|os|a|as)\s+(\d+)\s+mes", qn)
        if m:
            n=max(1,min(int(m.group(1)),24))
            months=[add_months(self.month,-i) for i in range(n)]
        elif "mes passado" in qn:
            months=[add_months(self.month,-1)]
        return months


    def _match_expense_term(self, term, rows):
        target=self._simple_word(term)
        exact=[]; fuzzy=[]
        if not target: return exact,fuzzy
        aliases=set(self.chat_aliases.get(target, [])) | {target}
        for r in rows:
            hay=self._norm(f"{r.get('description','')} {r.get('category','')}")
            words={self._simple_word(x) for x in hay.split()}
            if any(a in words or a in hay for a in aliases):
                exact.append(r); continue
            best_word=None; best=0
            for w in words:
                score=SequenceMatcher(None,target,w).ratio()
                if score>best: best,best_word=score,w
            if best>=0.80 and best_word:
                fuzzy.append((r,best_word,best))
        return exact,fuzzy


    def _extract_spend_term(self, q):
        qn=self._norm(q)
        patterns=[r"quanto (?:eu )?gastei (?:com|em) (.+)", r"gastos? (?:com|em) (.+)", r"total (?:de|com) (.+)"]
        for pat in patterns:
            m=re.search(pat,qn)
            if m:
                term=m.group(1).strip(" ?.!;")
                term=re.sub(r"\s+(?:este|nesse|neste|no|do) mes.*$", "", term).strip()
                term=re.sub(r"\s+nos? ultim.*$", "", term).strip()
                if term: return term
        return None


    def _handle_chat_confirmation(self, q):
        if not self.chat_pending: return None
        qn=self._norm(q)
        if qn in {"sim","s","pode","pode considerar","considera","considerar","correto","isso"}:
            p=self.chat_pending; self.chat_pending=None
            target=p["target"]
            self.chat_aliases.setdefault(target,[])
            for w in p["words"]:
                if w not in self.chat_aliases[target]: self.chat_aliases[target].append(w)
            rows=p["exact"]+[x[0] for x in p["fuzzy"]]
            total=sum(float(x.get("amount") or 0) for x in rows)
            return f"Confirmado. Considerando as grafias parecidas como a mesma coisa, encontrei {len(rows)} lançamento(s), totalizando {brl(total)}. Só usei lançamentos reais registrados no NexGrana."
        if qn in {"nao","não","n","nao considera","não considera","separado"}:
            p=self.chat_pending; self.chat_pending=None
            total=sum(float(x.get("amount") or 0) for x in p["exact"] )
            return f"Certo. Não considerei as grafias parecidas. Pelas correspondências exatas, encontrei {len(p['exact'])} lançamento(s), totalizando {brl(total)}."
        self.chat_pending = None
        return None


    def financial_chat_response(self, question):
        q = (question or "").lower().strip()
        qn = self._norm(q)
        who=(self.active_member() or {}).get("display_name") or "você"
        # Personalidade Nex: educado, curioso, levemente brincalhão e sério quando entra dinheiro real.
        # Pequeno papo não fica preso em uma pergunta financeira anterior.
        if any(x in qn for x in ["tudo bem", "tudo certo", "como voce esta", "como vc ta", "como voce ta"]):
            self.chat_context = None
            return f"Tudo certo por aqui, {who} 😄🦉. Tô de olho nas contas sem ficar paranoico kkkkk. E com você, hoje tá tranquilo ou o bolso inventou moda?"
        if qn in {"kkk","kkkk","kkkkk","rs","hahaha","haha"} or "kkkk" in qn:
            self.chat_context = None
            return "Aí sim kkkkk 🦉. Pode continuar, eu acompanho a conversa — não precisa falar comigo como se fosse formulário."
        if any(x in qn for x in ["obrigado", "obrigada", "valeu", "tmj", "tamo junto"]):
            return f"Tamo junto, {who}! 💜 Quando precisar, chama o Nex. E se eu viajar em algum cálculo, pode cobrar a coruja sem dó kkkkk."
        if any(x in qn for x in ["quem e voce", "quem é você", "o que voce faz", "o que vc faz"]):
            return "Eu sou o Nex 🦉, parceiro financeiro da NexGrana. Converso de forma leve, mas quando entro em saldo, despesas, metas ou parcelas eu uso os dados reais da família e prefiro dizer 'não sei' a inventar número."
        if any(x in qn for x in ["estou cansado", "to cansado", "tô cansado", "estou preocupado", "to preocupado", "tô preocupado"]):
            self.chat_memory["last_user_mood"] = "cansado/preocupado"
            return f"Entendi, {who}. Posso só trocar ideia com você ou, se a preocupação for dinheiro, a gente olha uma coisa por vez sem transformar isso numa palestra. O que tá pesando mais hoje?"
        if any(x in qn for x in ["estou feliz", "to feliz", "tô feliz", "deu certo", "consegui"]):
            self.chat_memory["last_user_mood"] = "feliz"
            return f"Boa, {who}! 🥳🦉 A coruja já quer jogar moeda pro alto kkkkk. Me conta o que deu certo."
        greetings = {"oi", "ola", "opa", "e ai", "bom dia", "boa tarde", "boa noite", "salve", "fala nex", "oi nex"}
        if qn in greetings:
            hour = datetime.now().hour
            period = "Bom dia" if hour < 12 else ("Boa tarde" if hour < 18 else "Boa noite")
            if "bom dia" in qn: period = "Bom dia"
            elif "boa tarde" in qn: period = "Boa tarde"
            elif "boa noite" in qn: period = "Boa noite"
            who=(self.active_member() or {}).get("display_name") or "meu caro"
            return f"{period}, {who}! 🦉 Tô por aqui. Quer conferir a grana da família, planejar alguma coisa ou só veio me dar um oi? 😄"
        if any(x in qn for x in ["obrigado", "valeu", "tmj", "tamo junto"]):
            return "Tamo junto! 🦉 Quando quiser olhar os números, eu puxo somente o que estiver registrado na sua conta."
        pending=self._handle_chat_confirmation(q)
        if pending:
            return pending

        # Personalidade social: conversa humana não fica presa em uma pergunta financeira anterior.
        who=(self.active_member() or {}).get("display_name") or "por aí"
        social_patterns = ["tudo certo", "tudo bem", "como voce esta", "como vc esta", "e voce", "e ai nex", "como foi seu dia"]
        if any(x in qn for x in social_patterns):
            # Mantém a intenção pendente em segundo plano, mas não força o usuário a responder naquele instante.
            pending_hint = " Quando quiser, a gente volta naquela compra." if self.chat_context else ""
            return f"Tudo certo por aqui, {who}! 🦉💜 Tô de olho na grana sem ficar neurótico kkkkk. E com você, como estão as coisas?{pending_hint}"
        if any(x in qn for x in ["kkkk", "kkk", "haha", "rsrs"]):
            return "kkkkkk aí sim 😄🦉. Pode falar normal comigo; se entrar dinheiro no assunto eu puxo os números reais, e se for só resenha eu acompanho também."
        if any(x in qn for x in ["to cansado", "estou cansado", "dia puxado", "dia dificil", "dia difícil"]):
            return f"Dia puxado, {who}? 😮‍💨 Então hoje eu não vou inventar palestra financeira não kkkkk. Se quiser, eu posso só te mostrar o essencial do mês em poucas linhas."

        # Conversa contextual: o Nex lembra quando acabou de pedir uma informação.
        if self.chat_context and self.chat_context.get("intent") == "purchase_amount":
            found=re.search(r"(?:r\$\s*)?(\d[\d\.]*[\,\.]?\d*)", q, re.I)
            purchase_followup = any(x in qn for x in ["compra", "custa", "valor", "preco", "preço", "reais", "r$"])
            if found:
                try:
                    value=money(found.group(1)); self.chat_context=None
                    d=self.dashboard_data(); available=float(d.get("balance") or 0); projected=float(d.get("projected_balance") or 0)
                    if value <= 0: return "Esse valor ficou estranho 😅. Me fala quanto custa a compra em reais."
                    if value <= max(projected,0):
                        return f"Pelos dados registrados, {brl(value)} cabe no saldo projetado atual ({brl(projected)}). Eu ainda preservaria uma margem para imprevistos antes de bater o martelo."
                    if value <= max(available,0):
                        return f"Hoje existe saldo para {brl(value)}, mas depois dos compromissos do mês o projetado é {brl(projected)}. Então eu classificaria como uma compra apertada, não como dinheiro realmente livre."
                    return f"Eu não trataria {brl(value)} como compra segura agora: o saldo disponível registrado é {brl(available)} e o projetado após compromissos é {brl(projected)}."
                except Exception:
                    pass
            if purchase_followup:
                return "Me manda só o valor aproximado da compra, por exemplo: R$ 850."
            # Mudou de assunto: não sequestra a conversa. O contexto fica guardado para quando ele voltar à compra.

        data = self.dashboard_data()
        analysis = self.financial_analysis()
        income = data["income"]
        expense = data["expense"]
        balance = data["balance"]
        projected = data["projected_balance"]

        # Fluxo guiado de Renda Extra — 8 dimensões, uma por vez.
        if self.chat_context and self.chat_context.get("intent") == "extra_income_profile":
            ctx=self.chat_context
            step=ctx.get("step","hours")
            bag=ctx.setdefault("data",{})
            if step=="hours":
                m=re.search(r"(\d+(?:[\.,]\d+)?)", qn)
                if not m:
                    return "Quantas horas por semana você consegue dedicar de verdade? Pode responder 4, 8, 12 horas…"
                bag["hours"]=float(m.group(1).replace(",","."))
                ctx["step"]="investment"
                return "Boa. Quanto você consegue investir para começar sem apertar as contas? R$ 0 também é resposta válida."
            if step=="investment":
                m=re.search(r"(?:r\$\s*)?(\d[\d\.]*[\,\.]?\d*)", q, re.I)
                if not m:
                    return "Me diga um teto de investimento inicial, por exemplo R$ 0, R$ 100 ou R$ 500."
                try: bag["investment"]=money(m.group(1))
                except Exception: bag["investment"]=0
                ctx["step"]="mode"
                return "Você prefere algo online, presencial ou tanto faz?"
            if step=="mode":
                mode=None
                if "online" in qn: mode="online"
                elif "presencial" in qn: mode="presencial"
                elif any(x in qn for x in ["tanto faz","indiferente","qualquer"]): mode="indiferente"
                if not mode:
                    return "Prefere online, presencial ou tanto faz?"
                bag["mode"]=mode
                ctx["step"]="skills"
                return "Que habilidades ou experiências você já tem? Ex.: cozinhar, dirigir, editar vídeo, vender, cuidar de pets, computador…"
            if step=="skills":
                if len(q.strip())<2:
                    return "Pode me contar pelo menos uma habilidade, experiência ou algo que você gosta de fazer."
                bag["skills"]=q.strip()
                ctx["step"]="equipment"
                return "Que recursos você já tem para começar? Ex.: celular bom, computador, carro/moto, ferramentas, cozinha equipada — ou ‘nenhum’."
            if step=="equipment":
                bag["equipment"]=q.strip()
                ctx["step"]="target"
                return "Qual seria uma meta de renda extra mensal para começar? Pode ser R$ 300, R$ 800, R$ 1.500…"
            if step=="target":
                m=re.search(r"(?:r\$\s*)?(\d[\d\.]*[\,\.]?\d*)", q, re.I)
                if not m:
                    return "Me passe uma meta mensal aproximada em reais. Ela não vira promessa; serve só para dimensionar o caminho."
                try: bag["target_income"]=money(m.group(1))
                except Exception: bag["target_income"]=0
                ctx["step"]="deadline"
                return "E em quanto tempo você gostaria de chegar perto dessa meta? Ex.: 30 dias, 3 meses, 6 meses."
            if step=="deadline":
                bag["deadline"]=q.strip()
                ctx["step"]="risk"
                return "Última: para começar, você prefere risco baixo, moderado ou aceita testar algo mais incerto em pequena escala?"
            if step=="risk":
                risk="moderado"
                if any(x in qn for x in ["baixo","conservador","pouco risco"]): risk="baixo"
                elif any(x in qn for x in ["alto","incerto","arriscar","agressivo"]): risk="alto"
                elif not any(x in qn for x in ["moderado","medio","médio","tanto faz"]):
                    return "Pode escolher: risco baixo, moderado ou alto (sempre começando pequeno)."
                bag["risk"]=risk
                hours=float(bag.get("hours") or 0)
                inv=float(bag.get("investment") or 0)
                mode=bag.get("mode","indiferente")
                skills=self._norm(bag.get("skills",""))
                equipment=self._norm(bag.get("equipment",""))
                target=float(bag.get("target_income") or 0)
                deadline=bag.get("deadline") or "sem prazo"
                candidates=[]
                for title,meta,guide in EXTRA_INCOME_MANUALS:
                    score=0
                    reasons=[]
                    meta_n=self._norm(meta); title_n=self._norm(title)
                    if mode=="online" and "online" in meta_n: score+=3; reasons.append("combina com sua preferência online")
                    if mode=="presencial" and "presencial" in meta_n: score+=3; reasons.append("combina com sua preferência presencial")
                    if mode=="indiferente": score+=1
                    if inv<=100 and ("baixo investimento" in meta_n or "quase sem investimento" in meta_n): score+=3; reasons.append("cabe melhor no investimento inicial")
                    elif inv<=500 and ("baixo" in meta_n or "medio" in meta_n): score+=2
                    elif inv>500: score+=1
                    keyword_groups={
                        "cozin": ["doces","marmitas"], "bolo":["doces"], "dirig":["entregas","fretes"],
                        "carro":["lavagem","entregas"], "moto":["entregas"], "video":["edicao de videos"], "edit":["edicao de videos"],
                        "pet":["cuidados com pets"], "animal":["cuidados com pets"], "foto":["fotografia"],
                        "venda":["revenda","brecho"], "roupa":["brecho"], "aula":["aulas particulares"],
                        "computador":["edicao de videos","fotografia"], "artesan":["artesanato"],
                    }
                    combined=skills+" "+equipment
                    for k,terms in keyword_groups.items():
                        if k in combined and any(t in title_n for t in terms): score+=4; reasons.append("aproveita algo que você já tem/sabe")
                    if hours and hours<4 and any(x in meta_n for x in ["flexivel","online"]): score+=1
                    if risk=="baixo" and ("baixo investimento" in meta_n or "quase sem investimento" in meta_n): score+=2; reasons.append("permite testar com exposição menor")
                    candidates.append((score,title,meta,guide,reasons[:3]))
                candidates=sorted(candidates,key=lambda x:x[0],reverse=True)[:3]
                self.chat_context=None
                lines=[]
                for i,(score,title,meta,guide,reasons) in enumerate(candidates,1):
                    why="; ".join(reasons) if reasons else "é uma opção simples para testar pequeno e medir o resultado"
                    lines.append(f"{i}. {title} — {meta}. Por que entrou: {why}. Primeiro experimento: {guide.split('.')[0].strip()}.")
                return (f"Fechei seu diagnóstico, {who}. Perfil: {hours:g}h/semana, até {brl(inv)} para começar, preferência {mode}, meta de {brl(target)}/mês, prazo ‘{deadline}’ e risco {risk}. "
                        "Isso não é promessa de ganho: vamos validar custo, tempo e demanda reais.\n\n" + "\n".join(lines) +
                        "\n\nEscolha uma pelo nome. Eu monto uma Trilha Nex de 10 etapas com checkpoints, custos, preço, clientes, resultado e lembretes opcionais.")

        # Início do diagnóstico de renda extra.
        if any(x in qn for x in ["quero uma renda extra", "me ajude a escolher", "ajuda a escolher uma renda extra", "encontrar uma renda extra"]):
            self.chat_context={"intent":"extra_income_profile","step":"hours","data":{}}
            return "Bora montar isso direito 🦉. Vou avaliar 8 dimensões rápidas e te devolver caminhos compatíveis. Primeiro: quantas horas por semana você consegue dedicar de verdade?"

        # Contexto vindo da Trilha Nex.
        m_trilha=re.search(r"quero montar uma renda extra com (.+?)(?:\.|$)", qn)
        if m_trilha:
            title=m_trilha.group(1).strip().title()
            match=next(((t,m,g) for t,m,g in EXTRA_INCOME_MANUALS if self._norm(t) in qn or self._norm(title) in self._norm(t)),None)
            if match:
                t,meta,guide=match
                return (f"Vamos transformar {t} em uma Trilha Nex prática, sem promessa de ganho.\n"
                        f"1) Escolher e validar a atividade: {guide}\n"
                        "2) Avaliar sua situação: tempo, capital, habilidades e recursos.\n"
                        "3) Aprender o básico antes de gastar.\n"
                        "4) Calcular custos reais: material, deslocamento, tempo, taxas e perdas.\n"
                        "5) Definir preço e margem mínima.\n"
                        "6) Buscar os primeiros clientes com um teste pequeno.\n"
                        "7) Registrar a primeira venda real.\n"
                        "8) Registrar custos e interpretar o lucro sem duplicar lançamentos.\n"
                        "9) Revisar resultado, horas, recorrência e feedback.\n"
                        "10) Decidir se vale continuar, ajustar, pausar ou ampliar.\n\n"
                        "Podemos começar pela etapa 1 e eu acompanho uma missão por vez. As anotações da trilha não viram lançamento financeiro automaticamente.")

        # Simulação detalhada de metas do Planejamento.
        if ("simular" in qn and "meta" in qn) or "simular alternativas para a meta" in qn:
            try:
                goals=self.cloud.list_goals() or []
                goal=None
                for g in goals:
                    if self._norm(g.get("name","")) and self._norm(g.get("name","")) in qn:
                        goal=g; break
                if not goal:
                    names=", ".join(g.get("name","Meta") for g in goals[:6]) or "nenhuma meta ativa"
                    return f"Não consegui identificar qual meta você quer simular. Metas que encontrei: {names}."
                target=float(goal.get("target_amount") or 0); saved=float(goal.get("saved_amount") or 0); remaining=max(target-saved,0)
                td=datetime.fromisoformat(str(goal.get("target_date"))[:10]).date()
                today=date.today()
                months=max(1,(td.year-today.year)*12+(td.month-today.month)+(1 if td.day>=today.day else 0))
                need=remaining/months
                free=float(analysis.get("free_margin") or 0)
                projected=float(data.get("projected_balance") or 0)
                one_more=remaining/(months+1); two_more=remaining/(months+2)
                entry=min(100.0,remaining,max(projected,0)) if remaining>0 else 0
                after_entry=max(remaining-entry,0)/months if months else 0
                if remaining<=0:
                    rec="Essa meta já está financeiramente completa pelos valores registrados."
                elif free>=need:
                    rec=f"O ritmo atual cabe na margem mensal registrada ({brl(free)}), mas eu ainda preservaria uma folga para imprevistos."
                elif free>0:
                    rec=f"O prazo atual pede {brl(need)}/mês, acima da margem mensal registrada de {brl(free)}. Alongar o prazo é a alternativa mais conservadora."
                else:
                    rec="A margem mensal registrada está zerada/negativa; eu não forçaria aportes antes de revisar gastos e próximos compromissos."
                entry_line=(f"• Se aportar {brl(entry)} agora: restariam {brl(max(remaining-entry,0))} e o ritmo cairia para {brl(after_entry)}/mês.\n" if entry>0 else "")
                return (f"Simulação da meta {goal.get('name')}:\n"
                        f"• Objetivo: {brl(target)} | já guardado: {brl(saved)} | falta: {brl(remaining)}.\n"
                        f"• Prazo registrado: {td.strftime('%d/%m/%Y')} (~{months} mês(es)).\n"
                        f"• Para manter o prazo: {brl(need)}/mês.\n"
                        f"• Se alongar 1 mês: {brl(one_more)}/mês.\n"
                        f"• Se alongar 2 meses: {brl(two_more)}/mês.\n"
                        f"{entry_line}"
                        f"• Margem do mês registrada: {brl(free)} | saldo projetado após compromissos: {brl(projected)}.\n\n"
                        f"🦉 Nex recomenda: {rec} Esses cenários são simulações; eu não movo dinheiro automaticamente.")
            except Exception as ex:
                return f"Não consegui montar a simulação agora ({type(ex).__name__}). Não vou inventar valores; tente novamente em instantes."

        context = ""
        if income > 0:
            ratio = expense / income * 100
            context = (
                f"\n\nNa sua conta neste mês: renda {brl(income)}, despesas {brl(expense)}, "
                f"saldo {brl(balance)} e comprometimento de {ratio:.1f}% da renda."
            )

        # Perguntas naturais mais comuns — resposta direta, sem texto genérico.
        if any(x in qn for x in ["como esta meu mes", "como ta meu mes", "resumo do mes", "meu mes"]):
            pending=float(data.get("pending_month") or 0); projected=float(data.get("projected_balance") or 0)
            top=(data.get("categories") or [])[:1]
            extra=f" Seu maior grupo de gastos é {top[0][0]} ({brl(top[0][1])})." if top else ""
            return f"Seu mês está assim: entrou {brl(income)}, saíram {brl(expense)} já efetivados e o saldo disponível acumulado está em {brl(balance)}. Há {brl(pending)} em compromissos futuros; depois deles, o projetado fica em {brl(projected)}.{extra}"

        if any(x in qn for x in ["quem gastou mais", "quem gasta mais"]):
            pairs=[]
            for m in self.members():
                mid=str(m.get("id")); pairs.append((m.get("display_name") or "Pessoa", float(data.get("member_expense",{}).get(mid,0))))
            pairs=sorted(pairs,key=lambda x:x[1],reverse=True)
            if not pairs or pairs[0][1] <= 0: return "Ainda não tenho despesas efetivadas suficientes para comparar os participantes neste mês."
            txt="; ".join(f"{n}: {brl(v)}" for n,v in pairs)
            return f"Neste mês, pelos pagamentos registrados: {txt}. Quem aparece com maior valor efetivado é {pairs[0][0]}."

        if any(x in qn for x in ["proximas contas", "proximos compromissos", "o que vence", "contas futuras"]):
            pending=float(data.get("pending_month") or 0)
            return f"Você tem {brl(pending)} em compromissos futuros registrados para este mês. O saldo disponível é {brl(balance)} e, considerando esses compromissos, o projetado fica em {brl(data.get('projected_balance') or 0)}."

        if any(x in qn for x in ["como posso economizar", "me ajude a economizar", "onde posso economizar"]):
            actions=(analysis.get("actions") or [])[:3]
            if not actions: return "Ainda não encontrei padrão suficiente para sugerir cortes sem chutar. Continue registrando que eu vou ficando mais esperto 🦉."
            return "Eu começaria por aqui:\n" + "\n".join(f"• {a['title']}: {a['text']}" for a in actions)

        if any(x in qn for x in ["posso comprar", "posso fazer uma compra", "da pra comprar", "dá pra comprar"]) and not re.search(r"\d", qn):
            self.chat_context={"intent":"purchase_amount"}
            return f"Posso analisar. Quanto custa a compra? Hoje o saldo disponível é {brl(balance)} e eu também vou considerar os compromissos futuros, não só o dinheiro que aparece na tela."

        if any(x in qn for x in ["burro", "idiota", "inutil", "inútil"]) and "nex" in qn:
            return "Ô, pega leve com a coruja 😤🦉 kkkkk. Posso errar uma interpretação, mas se você me disser onde eu viajei eu corrijo com os dados reais."

        # Consulta textual de gastos: usa somente registros reais; similaridade exige confirmação.
        spend_term=self._extract_spend_term(q)
        if spend_term:
            try:
                months=self._expense_scope_from_question(q)
                all_rows=self.cloud.all_expenses_full()
                rows=[r for r in all_rows if r.get("month") in months and expense_status(r)=="paid"]
                # Intervalo explícito dd/mm[/aaaa] a dd/mm[/aaaa]. Nunca presume datas ausentes.
                qn=self._norm(q)
                dates=re.findall(r"(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?", q)
                if len(dates)>=2:
                    def mkdate(t):
                        day,mon,yr=t; yr=int(yr) if yr else int(self.month[3:]); yr=yr+2000 if yr<100 else yr
                        return datetime(yr,int(mon),int(day)).date()
                    d1,d2=mkdate(dates[0]),mkdate(dates[1]); lo,hi=min(d1,d2),max(d1,d2)
                    rows=[r for r in all_rows if r.get("expense_date") and lo<=day(r["expense_date"])<=hi]
                # Se o usuário citar um membro pelo nome, filtra pelo pagador registrado.
                for m in self.members():
                    mn=self._norm(m.get("display_name"))
                    if mn and re.search(rf"\b{re.escape(mn)}\b", qn):
                        rows=[r for r in rows if str(r.get("payer_member_id"))==str(m["id"])]
                        spend_term=re.sub(rf"\s+(?:com|do|da|de)\s+{re.escape(mn)}.*$","",self._norm(spend_term)).strip() or spend_term
                        break
                exact,fuzzy=self._match_expense_term(spend_term,rows)
                if fuzzy:
                    words=sorted({w for _,w,_ in fuzzy})
                    self.chat_pending={"target":self._simple_word(spend_term),"words":words,"exact":exact,"fuzzy":fuzzy}
                    exact_total=sum(float(x.get("amount") or 0) for x in exact)
                    maybe_total=sum(float(x[0].get("amount") or 0) for x in fuzzy)
                    return (f"Encontrei {len(exact)} correspondência(s) direta(s) de '{spend_term}' ({brl(exact_total)}) e também "
                            f"{len(fuzzy)} lançamento(s) com nome parecido: {', '.join(words)} ({brl(maybe_total)}). "
                            "Não vou misturar os valores sem sua autorização. Devo considerar esses nomes parecidos como a mesma coisa?")
                if exact:
                    total=sum(float(x.get("amount") or 0) for x in exact)
                    period=", ".join(month_label(m) for m in months)
                    return f"Nos dados reais de {period}, encontrei {len(exact)} lançamento(s) relacionado(s) a '{spend_term}', totalizando {brl(total)}."
                return f"Não encontrei nenhum lançamento registrado que corresponda a '{spend_term}' no período consultado. Não vou estimar nem inventar um valor."
            except Exception as ex:
                return f"Não consegui consultar os lançamentos agora ({ex}). Para evitar inventar dados, não vou estimar o resultado."

        # Perguntas pessoais baseadas nos dados da conta.
        if any(k in q for k in ["como dividir", "divisão da renda", "divisao da renda", "distribuir minha renda"]):
            if income <= 0:
                return "Cadastre sua renda do mês primeiro. Com ela eu consigo sugerir uma divisão adaptada à sua realidade."
            parts = ", ".join(
                f"{x['label']} {x['percent']}% ({brl(x['amount'])})"
                for x in analysis["allocation"]
            )
            return (
                f"Com os dados atuais, uma divisão indicativa é: {parts}. "
                "Use isso como ponto de partida, não como regra fixa. "
                "Se suas despesas essenciais ou dívidas mudarem, a divisão também deve mudar."
            )

        if any(k in q for k in ["quanto guardar", "quanto economizar", "quanto reservar"]):
            if income <= 0:
                return "Cadastre a renda para eu calcular uma sugestão em reais."
            reserve = next((x for x in analysis["allocation"] if x["label"] == "Reserva"), None)
            if reserve:
                return (
                    f"Neste mês, a sugestão de reserva do NexGrana é cerca de {brl(reserve['amount'])} "
                    f"({reserve['percent']}% da renda). Seu saldo atual é {brl(balance)}. "
                    "Se houver dívida cara ou parcelas relevantes, vale ajustar esse valor para não apertar o caixa."
                )

        if any(k in q for k in ["quanto tenho em parcela", "parcelas futuras", "quanto de parcela", "parcelamento futuro"]):
            return (
                f"Há aproximadamente {brl(analysis['future_installments'])} em parcelas registradas para meses futuros. "
                "Compare esse valor com a renda dos próximos meses antes de assumir novos compromissos."
            )

        if any(k in q for k in ["posso comprar", "aquisição", "aquisicao", "aquisições", "aquisicoes", "qual compra", "qual item"]):
            acqs = self.cloud.list_acquisitions(True)
            if not acqs:
                return "Você ainda não tem aquisições ativas. Cadastre algo que quer comprar e eu comparo com seu saldo, prioridades e próximas contas."
            # Entende limites escritos de forma natural: "até 50", "uns 50 reais", "por 70".
            mval = re.search(r"(?:ate|até|uns?|por|de)\s*(?:r\$\s*)?(\d+(?:[\.,]\d{1,2})?)", qn)
            limit = float(mval.group(1).replace(",", ".")) if mval else None
            rows=[]
            for a in acqs:
                missing=max(float(a.get("estimated") or 0)-float(a.get("saved") or 0),0)
                rows.append((missing,a))
            if limit is not None:
                fits=[z for z in rows if z[0] <= limit]
                if fits:
                    fits.sort(key=lambda z: ({"Alta":0,"Média":1,"Baixa":2}.get(z[1].get("priority"),3), z[0]))
                    missing,best=fits[0]
                    return (
                        f"Até {brl(limit)}, a opção que melhor encaixa entre suas aquisições é {best.get('item')} "
                        f"({best.get('priority','Média')}), faltando {brl(missing)}. "
                        f"Seu saldo disponível é {brl(balance)} e eu também considerei o projetado de {brl(projected)}. "
                        "Se quiser, eu comparo comprar agora versus transformar em meta."
                    )
                nearest=min(rows,key=lambda z:abs(z[0]-limit))
                return (
                    f"Até {brl(limit)} eu não encontrei nenhuma aquisição que caiba inteira. "
                    f"A mais próxima é {nearest[1].get('item')}, faltando {brl(nearest[0])}. "
                    "Posso analisar se vale esperar, aumentar um pouco o limite ou transformar isso em meta."
                )
            mood,rec_text,rec=self._acquisition_recommendation(acqs)
            return rec_text + " Quer que eu compare essa opção com outra aquisição sua?"

        if any(k in q for k in ["como estou", "saúde financeira", "saude financeira", "situação financeira", "situacao financeira"]):
            if income <= 0:
                return "Cadastre a renda do mês para eu calcular sua saúde financeira."
            return (
                f"Sua saúde financeira do mês está classificada como {analysis['health']}. "
                f"Renda: {brl(income)}, despesas: {brl(expense)}, saldo: {brl(balance)}. "
                f"{analysis['health_detail']}."
            )

        # Análise de categoria usando os dados reais.
        for cat, val in data["categories"]:
            if cat.lower() in q:
                pct = (val / income * 100) if income else 0
                return (
                    f"Neste mês, {cat} soma {brl(val)}"
                    + (f", equivalente a {pct:.1f}% da renda." if income else ".")
                    + " Compare esse gasto com suas despesas essenciais, metas e reserva."
                )

        # Base educacional ampla.
        for topic in FINANCIAL_KNOWLEDGE:
            if any(keyword in q for keyword in topic["keywords"]):
                return f"{topic['title']}: {topic['text']}{context}"

        # Perguntas comparativas comuns.
        if "cdb" in q and "tesouro" in q:
            return (
                "CDB e Tesouro podem atender objetivos diferentes. Compare risco de crédito/emissor, liquidez, prazo, "
                "rentabilidade líquida de impostos e condições de resgate. Para reserva de emergência, a prioridade costuma ser "
                "baixo risco e alta liquidez; para outros objetivos, prazo e risco podem mudar a escolha."
                + context
            )

        if "poupança" in q or "poupanca" in q:
            return (
                "A poupança é simples e líquida, mas não deve ser comparada apenas pela facilidade. "
                "Compare rendimento líquido, inflação, liquidez e risco com outras alternativas adequadas ao seu objetivo."
                + context
            )

        if "melhor investimento" in q or "qual investimento" in q:
            return (
                "Não existe um único 'melhor investimento'. O mais adequado depende do objetivo, prazo, necessidade de liquidez "
                "e tolerância a risco. Se você me disser para que é o dinheiro e quando pretende usar, eu consigo organizar os critérios de comparação."
                + context
            )

        # Fallback adaptativo: responde com o contexto do perfil/mês em vez de um FAQ rígido.
        who=(self.active_member() or {}).get("display_name") or "você"
        if "porque" in qn or "por que" in qn:
            return f"Boa pergunta, {who}. Eu não quero chutar a causa sem dado suficiente. Se você me disser qual gasto, meta ou mudança chamou sua atenção, eu cruzo com o que está registrado e te explico passo a passo."
        if qn.endswith("?"):
            return (f"Entendi a pergunta, {who}, mas ainda não tenho uma resposta confiável para esse jeito de perguntar. "
                    f"Posso continuar com você em linguagem normal: me diga o que quer decidir e, se envolver dinheiro, eu uso o saldo {brl(balance)}, compromissos e histórico registrados — sem inventar valor.")
        return f"Tô acompanhando, {who} 🦉. Continua — não precisa escrever como comando. Se isso virar uma decisão financeira, eu conecto a conversa aos seus dados reais."


