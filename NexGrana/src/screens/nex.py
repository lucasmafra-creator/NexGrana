from ui.common import Context, EXTRA_INCOME_MANUALS, FINANCIAL_KNOWLEDGE, NexEvent, SequenceMatcher, add_months, brl, date, datetime, day, expense_status, member_expense_rows, ft, money, month_label, re, unicodedata, uuid, asyncio, logger
from services.nex_conversation import ChatScope, chat_scope_context, same_chat_context, same_chat_data_scope
from services.chat_retention import PERIODS, interval, in_interval, retain_messages, timestamp
from datetime import timezone

class NexScreen:
    MAX_PINNED_CONVERSATIONS = 5

    def _chat_scope_key(self, user_id=None, household_id=None, member_id=None):
        if user_id is None:
            user_id = str(getattr(getattr(self.cloud, "user", None), "id", ""))
        if household_id is None:
            household_id = str((getattr(self.cloud, "household", None) or {}).get("id") or "")
        if member_id is None:
            member_id = str(self.active_member_id or "")
        return f"nex-chat:{str(user_id)}:{str(household_id)}:{str(member_id or '')}"

    def _read_chat_store(self, scope_key=None):
        key = scope_key or self._chat_scope_key()
        default = {"free": {"messages": []}, "pinned": [], "archived": []}
        vault = getattr(self.cloud, "vault", None)
        if vault:
            value = vault.read(key, default)
        else:
            value = self._conversation_store_memory.get(key, default)
        if not isinstance(value, dict):
            value = default
        value.setdefault("free", {"messages": []})
        value.setdefault("pinned", [])
        value.setdefault("archived", [])
        return value

    def _write_chat_store(self, value, scope_key=None):
        key = scope_key or self._chat_scope_key()
        vault = getattr(self.cloud, "vault", None)
        if vault:
            vault.write(key, value)
        else:
            self._conversation_store_memory[key] = value

    def _hydrate_chat_store_from_cloud(self, store):
        if store.get("cloud_loaded") or not hasattr(self.cloud,"nex_conversation_bundle"):
            return store
        scope_key=self._chat_scope_key()
        try:
            rows=list(self.cloud.nex_conversation_bundle(self.active_member_id))
            if self._chat_scope_key()!=scope_key:return store
            tombstones=store.setdefault('message_tombstones',[])
            known={t['id'] for t in tombstones}
            for row in rows:
                local_id='free' if row.get('kind')=='free' and row.get('status')=='active' else str(row.get('id'))
                for purge in row.get('message_purges',[]):
                    if purge['id'] not in known:
                        tombstones.append({'id':purge['id'],'conversation_id':local_id,'remote_id':str(row['id']),
                            'start':purge['range_start'],'end':purge['range_end'],'state':'synced'})
                        known.add(purge['id'])
            free=next((row for row in rows if row.get("kind")=="free" and row.get("status")=="active"),None)
            pinned=[row for row in rows if row.get("kind")=="pinned" and row.get("status")=="active"]
            def messages(row):
                return [{"role":m.get("logical_role"),"text":m.get("content"),"request_id":m.get("request_id"),"state":m.get("state","synced"),"created_at":m.get("created_at")}
                        for m in (row or {}).get("messages",[]) if m.get("logical_role") in ("user","assistant")]
            def merge(local, remote):
                index={(m.get("request_id"),m.get("role")):m for m in remote if m.get("request_id")}
                result=[]
                seen=set()
                for msg in local:
                    identity=(msg.get("request_id"),msg.get("role")); server=index.get(identity)
                    if server and server.get("state")=="deleted":continue
                    result.append({**msg,**({"created_at":server.get("created_at"),"state":"synced"} if server else {})})
                    seen.add(identity)
                result.extend(m for m in remote if (m.get("request_id"),m.get("role")) not in seen and m.get("state")!="deleted")
                result.sort(key=lambda m:timestamp(m.get('created_at')) or datetime.min.replace(tzinfo=timezone.utc))
                return result[-120:]
            if free:
                local_free=dict(store.get("free") or {})
                local_free["remote_id"]=str(free.get("id"))
                local_free["messages"]=merge(local_free.get("messages",[]),messages(free))
                local_free["updated_at"]=free.get("updated_at")
                store["free"]=local_free
            if pinned and not store.get("pinned"):
                store["pinned"]=[{"id":str(row.get("id")),"title":row.get("title") or "Conversa fixada",
                    "messages":messages(row),"created_at":row.get("created_at"),"updated_at":row.get("updated_at"),"remote":True}
                    for row in sorted(pinned,key=lambda item:int(item.get("pinned_slot") or 99))]
            else:
                for local in store.get("pinned",[]):
                    remote=next((r for r in pinned if str(r.get("id"))==str(local.get("id"))),None)
                    if remote:local["messages"]=merge(local.get("messages",[]),messages(remote))
            store["cloud_loaded"]=True
            self._write_chat_store(store,scope_key)
        except Exception as exc:
            logger.warning("nex_conversation_hydration_failed kind=%s",type(exc).__name__)
        return store

    def _remote_conversation_id(self, store, conversation_id=None, member_id=None, scope_key=None):
        conversation_id = str(conversation_id if conversation_id is not None else self.conversation_id or "free")
        member_id = member_id if member_id is not None else self.active_member_id
        if conversation_id == "free":
            remote=(store.get("free") or {}).get("remote_id")
            if remote:return str(remote)
            row=self.cloud.ensure_free_nex_conversation(member_id)
            remote=str(row.get("id"))
            store.setdefault("free",{})["remote_id"]=remote
            self._write_chat_store(store,scope_key)
            return remote
        row=next((item for item in store.get("pinned",[]) if str(item.get("id"))==conversation_id),None)
        return str((row or {}).get("id") or "") or None

    def _same_chat_owner(self, scope):
        current_user=str(getattr(getattr(self.cloud,"user",None),"id",""))
        current_household=str(self.cloud._hid())
        current_member=str(self.active_member_id or "")
        return (scope.user_id,scope.household_id,scope.member_id)==(current_user,current_household,current_member)

    def _sync_chat_message(self,message,scope=None):
        if not message.get("request_id") or not hasattr(self.cloud,"save_nex_message"):
            return
        if scope is not None and not self._same_chat_owner(scope):
            message["state"]="pending"
            return
        try:
            scope_key=(self._chat_scope_key(scope.user_id,scope.household_id,scope.member_id) if scope is not None else None)
            conversation_id=(scope.conversation_id if scope is not None else self.conversation_id)
            member_id=(scope.member_id if scope is not None else self.active_member_id)
            store=self._read_chat_store(scope_key)
            remote=self._remote_conversation_id(store,conversation_id,member_id,scope_key)
            if not remote:return
            result=self.cloud.save_nex_message(remote,member_id,message.get("role"),message.get("text"),message.get("request_id"),created_at=message.get("created_at"))
            data=getattr(result,"data",{}) or {}
            message["state"]="deleted" if isinstance(data,dict) and data.get("state")=="deleted" else "synced"
        except Exception as exc:
            message["state"]="pending"
            logger.warning("nex_message_sync_pending kind=%s",type(exc).__name__)

    @staticmethod
    def _conversation_title(messages):
        first = next((m.get("text", "") for m in messages if m.get("role") == "user"), "")
        clean = " ".join(str(first).split())
        return (clean[:42] + "…") if len(clean) > 42 else (clean or "Conversa com o Nex")

    def _load_active_conversation(self, force=False):
        scope = self._chat_scope_key()
        if not force and self._loaded_chat_scope == scope:
            return
        store = self._read_chat_store()
        self._sync_chat_deletions(store,scope)
        if force:store["cloud_loaded"]=False
        store = self._hydrate_chat_store_from_cloud(store)
        selected = None
        if self.conversation_id != "free":
            selected = next((row for row in store["pinned"] if str(row.get("id")) == str(self.conversation_id)), None)
        if selected is None:
            self.conversation_id = "free"
            selected = store["free"]
        self.chat_messages = retain_messages(selected.get("messages",[]),store.get("message_tombstones",[]),self.conversation_id)[-120:]
        self._loaded_chat_scope = scope

    def _persist_chat_messages(self, messages, conversation_id, scope_key=None):
        store = self._read_chat_store(scope_key)
        messages = retain_messages(messages[-120:],store.get("message_tombstones",[]),conversation_id)
        if str(conversation_id or "free") == "free":
            free=dict(store.get("free") or {})
            free.update({"messages": messages, "updated_at": datetime.now().isoformat()})
            store["free"] = free
        else:
            row = next((item for item in store["pinned"] if str(item.get("id")) == str(conversation_id)), None)
            if row is not None:
                row["messages"] = messages
                row["updated_at"] = datetime.now().isoformat()
        self._write_chat_store(store,scope_key)

    def _persist_active_conversation(self):
        self._persist_chat_messages(self.chat_messages,self.conversation_id)

    def _sync_chat_deletions(self,store,scope_key):
        if not hasattr(self.cloud,"purge_nex_messages"):return
        if self._chat_scope_key()!=scope_key:return
        member_id=self.active_member_id
        changed=False
        for deletion in store.get("message_tombstones",[]):
            if self._chat_scope_key()!=scope_key:break
            if deletion.get("state")=="synced":continue
            try:
                remote=deletion.get("remote_id") or self._remote_conversation_id(store,deletion["conversation_id"],member_id,scope_key)
                if not remote:continue
                self.cloud.purge_nex_messages(remote,member_id,deletion["start"],deletion["end"],preview=False)
                deletion.update(state="synced",remote_id=remote);changed=True
            except Exception as exc:
                logger.warning("nex_deletion_pending kind=%s",type(exc).__name__)
                break
        if changed:
            latest=self._read_chat_store(scope_key)
            updates={t["id"]:t for t in store.get("message_tombstones",[])}
            latest["message_tombstones"]=[updates.get(t["id"],t) for t in latest.get("message_tombstones",[])]
            self._write_chat_store(latest,scope_key)

    def _refresh_chat_history(self,e=None):
        if self.nex_busy:
            self.snack("Aguarde a resposta antes de atualizar a conversa.");return
        self._load_active_conversation(force=True)
        self._refresh_nex_runtime()

    def clear_nex_messages_dialog(self,e=None):
        if self.nex_busy:
            self.snack("Aguarde a resposta antes de limpar mensagens.");return
        scope=self._current_chat_scope()
        key=self._chat_scope_key(scope.user_id,scope.household_id,scope.member_id)
        period=ft.Dropdown(label="Período",value="day",options=[ft.DropdownOption(k,label=v) for k,v in PERIODS.items()])
        description=ft.Text(size=11)
        confirm=ft.Button("Apagar mensagens deste período",icon=ft.Icons.DELETE_OUTLINE)
        chosen={}
        async def preview(e=None):
            start,end=interval(period.value)
            count=sum(in_interval(m,start,end) for m in self.chat_messages)
            chosen.update(start=start,end=end,count=count,remote=None)
            description.value=f"{count} mensagem(ns) neste aparelho. Intervalo: {datetime.fromisoformat(start).astimezone():%d/%m/%Y %H:%M} a {datetime.fromisoformat(end).astimezone():%d/%m/%Y %H:%M}. Mensagens sem data ficam preservadas."
            confirm.disabled=True;self.page.update()
            try:
                store=self._read_chat_store(key)
                remote=self._remote_conversation_id(store,scope.conversation_id,scope.member_id,key) if hasattr(self.cloud,"purge_nex_messages") else None
                if remote:
                    total=await asyncio.to_thread(self.cloud.purge_nex_messages,remote,scope.member_id,start,end,True)
                    if chosen.get("start")==start:
                        chosen.update(count=max(count,int(total or 0)),remote=remote)
                        description.value+=f" Na nuvem: {int(total or 0)}."
            except Exception:
                description.value+=" Sem conferência da nuvem: a exclusão do intervalo ficará pendente e poderá abranger outras mensagens desta conversa ao sincronizar."
            if self._chat_scope_matches_current(scope):
                confirm.disabled=chosen["count"]==0;self.page.update()
        async def remove(e):
            if self.nex_busy or not self._chat_scope_matches_current(scope):
                self.snack("A conversa ou perfil mudou. Abra a limpeza novamente.",True);return
            store=self._read_chat_store(key)
            store.setdefault("message_tombstones",[]).append({
                "id":str(uuid.uuid4()),"conversation_id":scope.conversation_id,
                "remote_id":chosen.get("remote"),"start":chosen["start"],"end":chosen["end"],"state":"pending",
            })
            self._write_chat_store(store,key)
            self.chat_messages=retain_messages(self.chat_messages,store["message_tombstones"],scope.conversation_id)
            target=store.get("free",{}) if scope.conversation_id=="free" else next((r for r in store.get("pinned",[]) if str(r.get("id"))==scope.conversation_id),{})
            target["messages"]=retain_messages(target.get("messages",[]),store["message_tombstones"],scope.conversation_id)
            self._write_chat_store(store,key)
            self._persist_active_conversation()
            self.page.pop_dialog();self._refresh_nex_runtime()
            await asyncio.to_thread(self._sync_chat_deletions,store,key)
            pending=any(t.get("state")!="synced" for t in store["message_tombstones"])
            self.snack("Mensagens removidas neste aparelho; sincronização pendente." if pending else "Exclusão sincronizada. As outras conversas e os registros financeiros foram preservados.")
        period.on_select=lambda e:self.page.run_task(preview)
        confirm.on_click=remove
        self.page.show_dialog(ft.AlertDialog(title=ft.Text("Limpar mensagens desta conversa"),content=ft.Column(tight=True,controls=[period,description,ft.Text("A exclusão sincronizada não pode ser desfeita.",size=11)]),actions=[ft.TextButton("Cancelar",on_click=lambda e:self.page.pop_dialog()),confirm]))
        self.page.run_task(preview)

    def _select_conversation(self, conversation_id):
        self._persist_active_conversation()
        self.conversation_id = str(conversation_id or "free")
        self._loaded_chat_scope = None
        self.chat_messages.clear()
        self.chat_pending = self.chat_context = None
        self._load_active_conversation(force=True)
        self.render()

    def _show_pin_replace_dialog(self, store):
        pinned = list(store.get("pinned") or [])[:self.MAX_PINNED_CONVERSATIONS]
        if not pinned:
            self.snack("Não encontrei uma conversa fixada para substituir.", True)
            return

        def replace(row):
            self.page.pop_dialog()
            self._pin_free_conversation(replace_id=row.get("id"))

        width, height = self.dialog_dimensions(560, 520)
        dialog = ft.AlertDialog(
            title=ft.Text("Cinco assuntos já estão fixados"),
            content=ft.Column(
                width=width,
                height=height,
                scroll=ft.ScrollMode.AUTO,
                spacing=8,
                controls=[
                    ft.Text(
                        "Escolha qual conversa será arquivada. O histórico antigo será preservado e este assunto ocupará o lugar dela.",
                        size=11,
                        color=self.muted_color(),
                    ),
                    *[
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.PUSH_PIN, color="#8B7CFF"),
                            title=ft.Text(row.get("title") or "Conversa fixada", max_lines=2),
                            trailing=ft.TextButton("Substituir", on_click=lambda e, item=row: replace(item)),
                        )
                        for row in pinned
                    ],
                ],
            ),
            actions=[ft.TextButton("Cancelar", on_click=lambda e:self.page.pop_dialog())],
        )
        self.page.show_dialog(dialog)

    def _rename_pinned_conversation(self, row):
        title=ft.TextField(label="Nome do assunto",value=row.get("title") or "",max_length=120,autofocus=True)
        save_button=ft.Button("Salvar",icon=ft.Icons.SAVE_OUTLINED)
        dialog=ft.AlertDialog(
            title=ft.Text("Renomear conversa fixada"),
            content=ft.Column(tight=True,controls=[title,ft.Text("O nome ajuda a reencontrar o assunto; não altera o histórico.",size=10,color=self.muted_color())]),
            actions=[ft.TextButton("Cancelar",on_click=lambda e:self.page.pop_dialog()),save_button],
        )
        def save(e):
            clean=" ".join((title.value or "").split())
            if not clean:self.snack("Informe um nome para o assunto.",True);return
            store=self._read_chat_store()
            current=next((x for x in store.get("pinned",[]) if str(x.get("id"))==str(row.get("id"))),None)
            if not current:self.snack("A conversa não está mais disponível.",True);return
            current["title"]=clean[:120];current["updated_at"]=datetime.now().isoformat();self._write_chat_store(store)
            try:
                if row.get("remote") and hasattr(self.cloud,"update_nex_conversation"):
                    self.cloud.update_nex_conversation(row.get("id"),title=clean)
            except Exception as exc:
                logger.warning("nex_rename_sync_pending kind=%s",type(exc).__name__)
            self.page.pop_dialog();self.snack("Assunto renomeado.");self.render()
        save_button.on_click=save
        self.page.show_dialog(dialog)

    def _delete_pinned_conversation(self, row):
        delete_button=ft.Button("Excluir conversa",icon=ft.Icons.DELETE_FOREVER_OUTLINED)
        dialog=ft.AlertDialog(
            title=ft.Text("Excluir conversa fixada?"),
            content=ft.Text("O histórico desta conversa será removido da sua lista. Esta ação exige confirmação."),
            actions=[ft.TextButton("Cancelar",on_click=lambda e:self.page.pop_dialog()),delete_button],
        )
        def remove(e):
            store=self._read_chat_store()
            store["pinned"]=[x for x in store.get("pinned",[]) if str(x.get("id"))!=str(row.get("id"))]
            self._write_chat_store(store)
            try:
                if row.get("remote") and hasattr(self.cloud,"update_nex_conversation"):
                    self.cloud.update_nex_conversation(row.get("id"),status="deleted")
            except Exception as exc:
                logger.warning("nex_delete_sync_pending kind=%s",type(exc).__name__)
            if str(self.conversation_id)==str(row.get("id")):
                self.conversation_id="free";self._loaded_chat_scope=None;self.chat_messages.clear();self._load_active_conversation(force=True)
            self.page.pop_dialog();self.snack("Conversa excluída.");self.render()
        delete_button.on_click=remove
        self.page.show_dialog(dialog)

    def _show_conversation_manager(self, e=None):
        store=self._read_chat_store()
        rows=list(store.get("pinned") or [])
        width,height=self.dialog_dimensions(580,560)
        controls=[ft.ListTile(
            leading=ft.Icon(ft.Icons.PUSH_PIN,color="#8B7CFF"),
            title=ft.Text(row.get("title") or "Conversa fixada",max_lines=2),
            subtitle=ft.Text(f"{len(row.get('messages') or [])} mensagem(ns)",size=9,color=self.muted_color()),
            on_click=lambda e,item=row:(self.page.pop_dialog(),self._select_conversation(item.get("id"))),
            trailing=ft.PopupMenuButton(items=[
                ft.PopupMenuItem(content=ft.Text("Renomear"),on_click=lambda e,item=row:self._rename_pinned_conversation(item)),
                ft.PopupMenuItem(content=ft.Text("Excluir"),on_click=lambda e,item=row:self._delete_pinned_conversation(item)),
            ]),
        ) for row in rows]
        if not controls:controls=[ft.Text("Nenhum assunto fixado. Use o alfinete no chat livre para guardar até cinco conversas.",size=11,color=self.muted_color())]
        self.page.show_dialog(ft.AlertDialog(
            title=ft.Text("Conversas do perfil"),
            content=ft.Column(width=width,height=height,scroll=ft.ScrollMode.AUTO,controls=controls),
            actions=[ft.TextButton("Fechar",on_click=lambda e:self.page.pop_dialog())],
        ))

    def _pin_free_conversation(self, e=None, replace_id=None):
        if self.conversation_id != "free":
            self.snack("Esta conversa já está fixada.")
            return
        if not any(message.get("role") == "user" for message in self.chat_messages):
            self.snack("Converse com o Nex antes de fixar este assunto.")
            return
        store = self._read_chat_store()
        if len(store["pinned"]) >= self.MAX_PINNED_CONVERSATIONS and not replace_id:
            self._show_pin_replace_dialog(store)
            return
        replaced = next((item for item in store["pinned"] if str(item.get("id")) == str(replace_id)), None)
        if replace_id and replaced is None:
            self.snack("A conversa escolhida não está mais disponível. Abra a lista e tente novamente.", True)
            return
        row = {
            "id": str(uuid.uuid4()),
            "title": self._conversation_title(self.chat_messages),
            "messages": [dict(message) for message in self.chat_messages[-120:]],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
        try:
            if not hasattr(self.cloud,"ensure_free_nex_conversation") or not hasattr(self.cloud,"pin_nex_conversation"):
                raise RuntimeError("Sincronização de conversa indisponível")
            remote=self._remote_conversation_id(store)
            remote_replace = replaced.get("id") if replaced and replaced.get("remote") else None
            new_free=self.cloud.pin_nex_conversation(remote,row["title"],remote_replace)
            if new_free:
                row["id"]=remote
                row["remote"]=True
        except RuntimeError:
            new_free=None
        except Exception as exc:
            new_free=None
            logger.warning("nex_pin_sync_pending kind=%s",type(exc).__name__)
        if replaced:
            store["pinned"] = [item for item in store["pinned"] if str(item.get("id")) != str(replace_id)]
            replaced["status"] = "archived"
            replaced["archived_at"] = datetime.now().isoformat()
            store["archived"].append(replaced)
        store["pinned"].append(row)
        store["free"] = {"messages": [], "updated_at": datetime.now().isoformat(),"remote_id":new_free}
        self._write_chat_store(store)
        self.conversation_id = "free"
        self.chat_messages.clear()
        self.chat_pending = self.chat_context = None
        self.snack("Assunto fixado e conversa anterior arquivada." if replaced else "Assunto fixado. Um novo chat livre foi aberto.")
        self.render()

    def _archive_pinned_conversation(self, e=None):
        if self.conversation_id == "free":
            return
        store = self._read_chat_store()
        row = next((item for item in store["pinned"] if str(item.get("id")) == str(self.conversation_id)), None)
        if row:
            store["pinned"] = [item for item in store["pinned"] if str(item.get("id")) != str(self.conversation_id)]
            row["status"] = "archived"
            row["archived_at"] = datetime.now().isoformat()
            store["archived"].append(row)
            self._write_chat_store(store)
            try:
                if hasattr(self.cloud,"unpin_nex_conversation"):
                    self.cloud.unpin_nex_conversation(row.get("id"))
            except Exception as exc:
                logger.warning("nex_unpin_sync_pending kind=%s",type(exc).__name__)
        self.conversation_id = "free"
        self._loaded_chat_scope = None
        self.chat_messages.clear()
        self._load_active_conversation(force=True)
        self.snack("Conversa desafixada e preservada no arquivo.")
        self.render()

    def _nex_runtime(self):
        return getattr(self, "_nex_chat_runtime", None) or {}

    def _current_chat_scope(self, request_id=""):
        return ChatScope(
            user_id=str(getattr(getattr(self.cloud,"user",None),"id","")),
            household_id=str(self.cloud._hid()),
            member_id=str(self.active_member_id or ""),
            month=self.month,
            conversation_id=str(getattr(self,"conversation_id","") or "free"),
            session_generation=int(getattr(self,"_nex_session_generation",0)),
            request_id=str(request_id or ""),
        )

    def _chat_scope_matches_current(self, scope):
        try:
            return same_chat_context(scope,self._current_chat_scope())
        except Exception:
            return False

    def _chat_data_scope_matches_current(self, scope):
        try:
            return same_chat_data_scope(scope,self._current_chat_scope())
        except Exception:
            return False

    def _chat_runtime_matches(self, scope):
        runtime=self._nex_runtime()
        return bool(
            self.screen==4
            and self._chat_scope_matches_current(scope)
            and tuple(runtime.get("context") or ())==chat_scope_context(scope)
        )

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
                    ft.Image(src=self.nex_asset("idle","avatar",context="chat"),width=48 if phone else 54,height=48 if phone else 54,fit=ft.BoxFit.CONTAIN,gapless_playback=True),
                    ft.Container(expand=True,padding=12,border_radius=16,bgcolor=self.assistant_bubble_color(),content=ft.Text(msg.get("text") or "",size=12,selectable=True)),
                ],
            ),
        )

    def _refresh_nex_runtime(self):
        """Update mounted chat controls without replacing the composer/tree."""
        rt=self._nex_runtime()
        chat_list=rt.get("list")
        question=rt.get("question")
        send_button=rt.get("send")
        quick_buttons=rt.get("quick_buttons") or []
        status_text=rt.get("status_text")
        status_box=rt.get("status_box")
        if chat_list is None:
            return False
        phone=self._layout_bucket()=="phone"
        controls=chat_list.controls
        typing=rt.get("typing_control")
        if typing is not None:
            try:
                controls.remove(typing)
            except ValueError:
                pass
            rt["typing_control"]=None

        visible=[m for m in self.chat_messages if m.get('state') != 'deleted'][-80:]
        visible_ids=[id(message) for message in visible]
        rendered_ids=rt.get("rendered_message_ids") or []
        if visible_ids[:len(rendered_ids)]==rendered_ids:
            for message in visible[len(rendered_ids):]:
                controls.append(self._chat_bubble(message,phone))
        else:
            chat_list.controls=[self._chat_bubble(message,phone) for message in visible]
            controls=chat_list.controls
        rt["rendered_message_ids"]=visible_ids

        active_scope=getattr(self,"_nex_active_scope",None)
        view_scope=rt.get("context")
        busy_for_view=bool(
            self.nex_busy
            and active_scope is not None
            and tuple(view_scope or ())==chat_scope_context(active_scope)
        )
        if busy_for_view:
            typing=ft.Container(
                padding=ft.Padding.only(top=4,bottom=8),
                content=ft.Row(vertical_alignment=ft.CrossAxisAlignment.CENTER,controls=[
                    ft.Image(src=self.nex_asset("thinking","avatar",context="chat"),width=42 if phone else 48,height=42 if phone else 48,fit=ft.BoxFit.CONTAIN),
                    ft.Container(padding=10,border_radius=16,bgcolor=self.assistant_bubble_color(),content=ft.Text("Nex está pensando…",size=11,italic=True,color=self.muted_color())),
                ]),
            )
            controls.append(typing)
            rt["typing_control"]=typing
        if question is not None:
            # Keep the field enabled/mounted so response updates do not dismiss
            # the Android IME or rebuild its focus node.
            question.disabled=False
        if send_button is not None:
            send_button.disabled=self.nex_busy
        for btn in quick_buttons:
            btn.disabled=self.nex_busy
        if status_text is not None:
            state=getattr(self.nex_engine,"connection_state","local")
            labels={"online":"online confirmado","connecting":"conectando…","ready":"configurado, ainda não testado","offline":"indisponível • local","local":"local"}
            status_text.value=labels.get(state,"local")
            status_text.color=ft.Colors.GREEN_300 if state=="online" else self.muted_color()
            if status_box is not None:
                status_box.bgcolor="#173D2B" if state=="online" else self.surface_color()
        try:
            chat_list.update()
            if question is not None: question.update()
            if send_button is not None: send_button.update()
            for btn in quick_buttons: btn.update()
            if status_box is not None: status_box.update()
            return True
        except Exception:
            return False

    def _queue_nex_message(self, text, source="chat", entity_id=None, action=None, payload=None, question=None, runtime_token=None):
        """Queue once and leave the mounted Android composer focused."""
        q=(text or "").strip()
        if not q:
            return False
        if self.nex_busy:
            self.snack("O Nex ainda está terminando a resposta anterior.")
            return False
        runtime=self._nex_runtime()
        if runtime_token and runtime_token!=runtime.get("token"):
            return False
        scope=self._current_chat_scope(str(uuid.uuid4()))
        scope_key=self._chat_scope_key(scope.user_id,scope.household_id,scope.member_id)
        messages_snapshot=[dict(message) for message in self.chat_messages[-120:]]
        self.nex_busy=True
        self._nex_active_request_id=scope.request_id
        self._nex_active_scope=scope
        if question is not None:
            self.nex_draft=""
            question.value=""
            try:
                question.update()
            except Exception:
                pass
        # Disable only the action controls. The TextField remains mounted and
        # enabled, so its Android focus node/IME is not replaced on send.
        for control in [runtime.get("send"),*(runtime.get("quick_buttons") or [])]:
            if control is not None:
                control.disabled=True
                try:control.update()
                except Exception:pass
        try:
            self.page.run_task(
                self._dispatch_nex_message,q,source,entity_id,action,payload,
                scope,runtime_token,messages_snapshot,scope_key,
            )
        except Exception as exc:
            self.nex_busy=False
            self._nex_active_request_id=None
            self._nex_active_scope=None
            self.nex_draft=q
            if question is not None:
                question.value=q
                try:question.update()
                except Exception:pass
            logger.warning("nex_queue_failed kind=%s",type(exc).__name__)
            self.snack("Não consegui iniciar a resposta. Sua mensagem continua no campo para tentar novamente.",True)
            self._refresh_nex_runtime()
            return False
        return True

    async def _dispatch_nex_message(self, text, source="chat", entity_id=None, action=None, payload=None,
                                    scope=None, runtime_token=None, messages_snapshot=None, scope_key=None):
        q=(text or "").strip()
        if not q:
            return None
        if scope is None:
            scope=self._current_chat_scope(str(uuid.uuid4()))
        request_id=scope.request_id
        if self._nex_active_request_id!=request_id:
            return None
        if not self._chat_scope_matches_current(scope):
            logger.info("nex_queued_request_scope_changed")
            if self._nex_active_request_id==request_id:
                self._nex_active_request_id=None
                self._nex_active_scope=None
                self.nex_busy=False
                self.snack("O perfil, mês ou conversa mudou antes do envio. Confira o chat e tente novamente.",True)
                if self.screen==4:
                    self._refresh_nex_runtime()
            return None

        self.nex_busy=True
        self._nex_active_scope=scope
        self.nex_draft=""
        user_message={"role":"user","text":q,"request_id":request_id,"state":"pending","created_at":datetime.now(timezone.utc).isoformat()}
        if not any(item.get("request_id")==request_id and item.get("role")=="user" for item in self.chat_messages):
            self.chat_messages.append(user_message)
            self.chat_messages=self.chat_messages[-120:]
        else:
            user_message=next(item for item in self.chat_messages if item.get("request_id")==request_id and item.get("role")=="user")
        self._sync_chat_message(user_message,scope)
        request_messages=[dict(message) for message in self.chat_messages[-120:]]
        self._persist_chat_messages(request_messages,scope.conversation_id,scope_key)
        if self._chat_runtime_matches(scope):
            self.nex_event(NexEvent.CHAT_THINKING)
            self._refresh_nex_runtime()
        try:
            await asyncio.sleep(0)
            context=Context(
                source=source,
                household_id=scope.household_id,
                member_id=scope.member_id,
                month=scope.month,
                entity_id=str(entity_id) if entity_id is not None else None,
                action=action,
                payload=payload or {},
                request_id=request_id,
                conversation_id=scope.conversation_id,
                snapshot_reference=f"{scope.household_id}:{scope.member_id}:{scope.month}",
                history=tuple(dict(message) for message in request_messages),
            )
            response=await asyncio.to_thread(self.nex_engine.respond,q,context)
            current_scope=self._current_chat_scope(request_id)
            # User/profile/month changes invalidate a financial response. A
            # conversation switch in the same scope keeps the reply with its
            # original history instead of placing it in the newly opened chat.
            if not same_chat_data_scope(scope,current_scope):
                logger.info("nex_stale_data_scope_discarded")
                return None
            response=(response or "").strip() or "Não consegui montar uma resposta confiável agora. Não vou inventar dados; tente novamente."
            assistant_message={"role":"assistant","text":response,"request_id":request_id,"state":"pending","created_at":datetime.now(timezone.utc).isoformat()}
            same_conversation=same_chat_context(scope,current_scope)
            if same_conversation:
                existing=next((item for item in self.chat_messages if item.get("request_id")==request_id and item.get("role")=="assistant"),None)
                if existing:
                    assistant_message=existing
                else:
                    self.chat_messages.append(assistant_message)
                request_messages=[dict(message) for message in self.chat_messages[-120:]]
            else:
                request_messages.append(assistant_message)
                request_messages=request_messages[-120:]
            self._sync_chat_message(assistant_message,scope)
            self._persist_chat_messages(request_messages,scope.conversation_id,scope_key)
            if same_conversation and self._chat_runtime_matches(scope):
                self.nex_event(NexEvent.CHAT_REPLY)
                self._refresh_nex_runtime()
            try:
                self.analytics.track("nex_request_completed",source=source,result="success",latency_bucket=getattr(self.nex_engine,"last_mode","local"))
            except Exception:
                pass
            return response
        except Exception as exc:
            logger.warning("nex_dispatch_failed kind=%s",type(exc).__name__)
            try:
                current_scope=self._current_chat_scope(request_id)
            except Exception:
                current_scope=None
            if current_scope is not None and same_chat_data_scope(scope,current_scope):
                failure={"role":"assistant","text":"Tive um problema ao processar isso agora. Nenhum valor foi inventado. Tente novamente.","request_id":request_id,"state":"pending","created_at":datetime.now(timezone.utc).isoformat()}
                if same_chat_context(scope,current_scope):
                    self.chat_messages.append(failure)
                    request_messages=[dict(message) for message in self.chat_messages[-120:]]
                else:
                    request_messages.append(failure)
                    request_messages=request_messages[-120:]
                self._sync_chat_message(failure,scope)
                self._persist_chat_messages(request_messages,scope.conversation_id,scope_key)
                if same_chat_context(scope,current_scope) and self._chat_runtime_matches(scope):
                    self._refresh_nex_runtime()
            return None
        finally:
            if self._nex_active_request_id==request_id:
                self._nex_active_request_id=None
                self._nex_active_scope=None
                self.nex_busy=False
                if self.screen==4:
                    self._refresh_nex_runtime()

    def _process_nex_message(self, text, source="chat", entity_id=None):
        return self._queue_nex_message(text,source,entity_id)

    def _start_nex_topic(self, text, source="action", entity_id=None, action=None, payload=None):
        try:self.page.pop_dialog()
        except (IndexError, AssertionError, AttributeError):pass
        self._go_nex_chat()
        self._queue_nex_message(text,source,entity_id,action,payload)

    def chat_screen(self):
        phone=self._layout_bucket()=="phone"
        runtime_token=uuid.uuid4().hex
        runtime_context=chat_scope_context(self._current_chat_scope())
        self._load_active_conversation()
        if not self.chat_messages:
            hour=datetime.now().hour
            period="Bom dia" if hour<12 else ("Boa tarde" if hour<18 else "Boa noite")
            who=getattr(self,"nex_user_name",lambda:"")() or (self.active_member() or {}).get("display_name") or "por aí"
            self.chat_messages.append({"role":"assistant","text":f"{period}, {who}! 👋 Eu sou o Nex. Pode falar normal comigo. Quando eu usar números, eles vêm somente dos dados deste perfil. 🦉"})
            self._persist_active_conversation()

        chat_list=ft.ListView(expand=True,spacing=4,auto_scroll=True,scroll=ft.ScrollMode.AUTO,controls=[self._chat_bubble(m,phone) for m in self.chat_messages[-80:]])
        chat_surface=ft.Container(expand=True,bgcolor=self.page_color(),border_radius=14,
            border=ft.Border.all(1,self.border_color()),padding=8,content=chat_list)
        question=ft.TextField(
            value=self.nex_draft,
            hint_text="Fale com o Nex...",
            multiline=True,
            shift_enter=True,
            min_lines=1,
            max_lines=3 if phone else 4,
            expand=True,
            border_radius=16,
            disabled=False,
            text_size=16 if phone else 13,
        )
        mobile_focus_controls={}
        keyboard_close=None

        def _set_composer_focus(focused):
            self.nex_draft=(question.value or self.nex_draft or "") if not focused else self.nex_draft
            if not phone:return
            # O teclado Android compete com a NavigationBar. Durante digitação,
            # preservamos a área do composer e ocultamos conteúdo não essencial.
            if self.page.navigation_bar is not None:
                self.page.navigation_bar.visible=not focused
                try:self.page.navigation_bar.update()
                except Exception:pass
            # O cabeçalho permanece visível: no Android ele contém a saída da
            # conversa e não pode desaparecer enquanto o teclado está aberto.
            for key in ("hero","quick","spacer"):
                ctrl=mobile_focus_controls.get(key)
                if ctrl is not None:
                    ctrl.visible=not focused
                    try:ctrl.update()
                    except Exception:pass
            close_control=mobile_focus_controls.get("keyboard_close")
            if close_control is not None:
                close_control.visible=focused
                try:close_control.update()
                except Exception:pass

        def close_mobile_keyboard(e=None):
            # The tapped button removes focus through normal platform handling.
            # Keep the list/composer mounted so scroll and draft stay intact.
            self.nex_draft=question.value or ""
            _set_composer_focus(False)

        def submit(e=None):
            self._queue_nex_message(question.value,"chat",None,"message",{},question=question,runtime_token=runtime_token)

        question.on_submit=submit
        question.on_change=lambda e:setattr(self,"nex_draft",question.value or "")
        question.on_focus=lambda e:_set_composer_focus(True)
        question.on_blur=lambda e:_set_composer_focus(False)

        def quick_handler(text,action):
            return lambda e:self._queue_nex_message(text,"quick",None,action,{},runtime_token=runtime_token)

        active_name=(self.active_member() or {}).get("display_name") or self.space_copy("seu perfil","a família")
        mood,_=self._nex_suggestion()
        live_nex=ft.Container(
            width=60 if phone else 70,height=60 if phone else 70,
            offset=ft.Offset(0,0),scale=1.0,rotate=0,
            animate_offset=ft.Animation(850,ft.AnimationCurve.EASE_IN_OUT),
            animate_scale=ft.Animation(850,ft.AnimationCurve.EASE_IN_OUT),
            animate_rotation=ft.Animation(850,ft.AnimationCurve.EASE_IN_OUT),
            on_click=lambda e:self.page.run_task(self.nex_click_and_chat),tooltip="Toque no Nex",
            content=ft.Image(src=self.nex_asset(mood,"card",context="chat"),width=60 if phone else 70,height=60 if phone else 70,fit=ft.BoxFit.CONTAIN,gapless_playback=True),
        )
        self.nex_chat_live_control=live_nex
        hero=ft.Container(
            visible=not phone,
            padding=8,border_radius=14,bgcolor=self.surface_alt_color(),border=ft.Border.all(1,self.border_color()),
            content=ft.ResponsiveRow(vertical_alignment=ft.CrossAxisAlignment.CENTER,controls=[
                ft.Container(col={"xs":3,"sm":3},alignment=ft.Alignment.CENTER,content=live_nex),
                ft.Container(col={"xs":9,"sm":9},content=ft.Column(spacing=5,controls=[
                    ft.Text(f"Nex está com {active_name}",size=18,weight=ft.FontWeight.BOLD),
                    ft.Text("Consultas e simulações usam somente os registros do perfil selecionado. Se faltar dado, eu aviso — não chuto valor.",size=10,color=self.muted_color()),
                    ft.Text("🦉 Toque no Nex para uma reação.",size=9,color="#8B7CFF",italic=True),
                ])),
            ]),
        )
        quick_specs=[
            ("Como está meu mês?","month_summary"),
            (("Qual aquisição faz sentido agora?" if self.active_member_acquisitions(True) else "Posso comprar algo agora?"),"evaluate_acquisition"),
            ("Me ajude a economizar","save_money"),
            ("Próximas contas","next_bills"),
        ]
        quick_buttons=[]
        for text,action in quick_specs:
            btn=ft.OutlinedButton(text,col={"xs":6,"md":3},disabled=self.nex_busy,on_click=quick_handler(text,action))
            quick_buttons.append(btn)
        quick=ft.ResponsiveRow(spacing=6,run_spacing=6,controls=quick_buttons)
        quick.controls.append(ft.TextButton("Visual do Nex",icon=ft.Icons.PALETTE_OUTLINED,
            on_click=self.nex_skin_dialog,col={"xs":6,"md":3}))
        store=self._read_chat_store()
        active_conversation=next((row for row in store["pinned"] if str(row.get("id"))==str(self.conversation_id)),None)
        connection_state=getattr(self.nex_engine,"connection_state","local")
        connection_labels={"online":"online confirmado","connecting":"conectando…","ready":"configurado","offline":"indisponível • local","local":"local"}
        connection_text=ft.Text(connection_labels.get(connection_state,"local"),size=8,color=ft.Colors.GREEN_300 if connection_state=="online" else self.muted_color())
        connection_box=ft.Container(
            padding=ft.Padding.symmetric(horizontal=7,vertical=3),border_radius=12,
            bgcolor="#173D2B" if connection_state=="online" else self.surface_color(),content=connection_text,
        )
        conversation_bar=ft.Container(
            padding=ft.Padding.symmetric(horizontal=10,vertical=6),border_radius=14,bgcolor=self.surface_alt_color(),
            content=ft.Row(controls=[
                ft.Icon(ft.Icons.PUSH_PIN if active_conversation else ft.Icons.CHAT_BUBBLE_OUTLINE,size=18,color="#8B7CFF"),
                ft.Text((active_conversation or {}).get("title") or "Chat livre",expand=True,weight=ft.FontWeight.BOLD,size=11,max_lines=1,overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text(f"{len(store['pinned'])}/5",size=9,color=self.muted_color()),
                connection_box,
                ft.IconButton(ft.Icons.FOLDER_OPEN_OUTLINED,tooltip="Gerenciar conversas",on_click=self._show_conversation_manager),
                ft.PopupMenuButton(icon=ft.Icons.MORE_VERT,items=[
                    ft.PopupMenuItem(content=ft.Text("Atualizar conversa"),on_click=self._refresh_chat_history),
                    ft.PopupMenuItem(content=ft.Text("Limpar mensagens"),on_click=self.clear_nex_messages_dialog),
                ]),
                ft.IconButton(ft.Icons.PUSH_PIN_OUTLINED if not active_conversation else ft.Icons.PUSH_PIN,tooltip="Fixar assunto" if not active_conversation else "Desafixar e arquivar",on_click=self._pin_free_conversation if not active_conversation else self._archive_pinned_conversation),
            ]),
        )
        try:
            consent_cache=self.cloud._cache_get("privacy_consents_local",{}) or {}
            allowed=bool(consent_cache.get("external_ai"))
        except Exception:
            allowed=False
        if getattr(self.nex_engine,"gateway",None) and not allowed:
            mode_banner=ft.Container(padding=10,border_radius=12,bgcolor=self.surface_alt_color(),content=ft.Row(wrap=True,controls=[
                ft.Text("Quer conversar com respostas online? Veja quais dados são usados e escolha se deseja ativar.",expand=True,size=11),
                ft.OutlinedButton("Conhecer Nex online",on_click=lambda _:self.privacy_dialog()),
            ]))
        elif not getattr(self.nex_engine,"gateway",None):
            mode_banner=ft.Text("Nex em modo local: conversa online ainda não configurada nesta versão.",size=10,color=self.muted_color())
        else:
            mode_banner=ft.Text("Nex online configurado. O indicador só confirma conexão após uma resposta real.",size=10,color=self.muted_color())
        if phone:
            compact_month=ft.Row(
                spacing=0,
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.IconButton(ft.Icons.CHEVRON_LEFT,tooltip="Mês anterior",on_click=lambda e:self.change_month(-1)),
                    ft.Text(month_label(self.month),size=12,weight=ft.FontWeight.BOLD),
                    ft.IconButton(ft.Icons.CHEVRON_RIGHT,tooltip="Próximo mês",on_click=lambda e:self.change_month(1)),
                ],
            )
            screen_header=ft.Container(
                bgcolor=self.surface_color(),
                padding=ft.Padding.symmetric(horizontal=8,vertical=6),
                content=ft.Column(spacing=4,controls=[
                    ft.Row(spacing=4,controls=[
                        ft.TextButton("Voltar",icon=ft.Icons.ARROW_BACK,on_click=lambda e:self._back_from_nex()),
                        ft.Text("Nex",size=20,weight=ft.FontWeight.BOLD,expand=True),
                        ft.Container(width=150,content=self.profile_selector(compact=True)),
                    ]),
                    compact_month,
                ]),
            )
        else:
            screen_header=self.header("Nex","Seu parceiro financeiro inteligente")
        hero_wrap=ft.Container(content=hero)
        hero_spacer=ft.Container(height=12 if phone else 4)
        quick_wrap=ft.Container(content=quick)
        mobile_focus_controls.update({"header":screen_header,"hero":hero_wrap,"quick":quick_wrap,"spacer":hero_spacer})
        keyboard_close=ft.IconButton(
            ft.Icons.KEYBOARD_HIDE,
            tooltip="Fechar teclado sem enviar",
            data="nex-keyboard-close",
            visible=False,
            on_click=close_mobile_keyboard,
        )
        mobile_focus_controls["keyboard_close"]=keyboard_close
        send_button=ft.IconButton(ft.Icons.SEND_ROUNDED,tooltip="Enviar",disabled=self.nex_busy,on_click=submit)
        composer=ft.Container(
            bgcolor=self.surface_color(),border_radius=14,padding=ft.Padding.only(left=8,right=8,top=8,bottom=18 if phone else 8),
            content=ft.Row(vertical_alignment=ft.CrossAxisAlignment.END,controls=[question,keyboard_close,send_button]),
        )
        self._nex_chat_runtime={
            "list":chat_list,"question":question,"send":send_button,"quick_buttons":quick_buttons,
            "status_text":connection_text,"status_box":connection_box,"token":runtime_token,
            "context":runtime_context,"rendered_message_ids":[id(message) for message in self.chat_messages[-80:]],
            "typing_control":None,
        }
        if self.nex_busy:self._refresh_nex_runtime()
        return ft.Column(expand=True,spacing=0,controls=[
            screen_header,
            ft.Container(expand=True,bgcolor=self.surface_color(),padding=10 if phone else 14,content=ft.Column(expand=True,spacing=6 if phone else 8,controls=[
                hero_wrap,conversation_bar,mode_banner,chat_surface,quick_wrap,composer,
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
            return "Eu sou o Nex 🦉, parceiro financeiro da NexGrana. Converso de forma leve, mas quando entro em saldo, despesas, metas ou parcelas eu uso somente os dados do perfil selecionado e prefiro dizer 'não sei' a inventar número."
        if any(x in qn for x in ["estou cansado", "to cansado", "tô cansado", "estou preocupado", "to preocupado", "tô preocupado"]):
            self.chat_memory["last_user_mood"] = "cansado/preocupado"
            return f"Entendi, {who}. Posso só trocar ideia com você ou, se a preocupação for dinheiro, a gente olha uma coisa por vez sem transformar isso numa palestra. O que tá pesando mais hoje?"
        if any(x in qn for x in ["estou feliz", "to feliz", "tô feliz", "deu certo", "consegui"]):
            self.chat_memory["last_user_mood"] = "feliz"
            return f"Boa, {who}! 🥳🦉 A coruja já quer jogar moeda pro alto kkkkk. Me conta o que deu certo."
        greetings = {"oi", "ola", "opa", "e ai", "eae", "bom dia", "boa tarde", "boa noite", "salve", "fala nex", "oi nex", "suave", "suave nex", "blz", "beleza", "de boa", "fala bro"}
        if qn in greetings:
            hour = datetime.now().hour
            period = "Bom dia" if hour < 12 else ("Boa tarde" if hour < 18 else "Boa noite")
            if "bom dia" in qn: period = "Bom dia"
            elif "boa tarde" in qn: period = "Boa tarde"
            elif "boa noite" in qn: period = "Boa noite"
            who=(self.active_member() or {}).get("display_name") or "meu caro"
            return f"{period}, {who}! 🦉 Tô por aqui. Quer conferir seus registros, planejar alguma coisa ou só veio me dar um oi? 😄"
        if any(x in qn for x in ["curso de programacao", "cursos de programacao", "estudar programacao", "area de tecnologia", "carreira em tecnologia"]):
            return ("Bora por uma trilha que não dependa de moda: 1) lógica de programação; 2) Git e GitHub; "
                    "3) uma linguagem principal — Python ou JavaScript são boas portas de entrada; 4) banco de dados e SQL; "
                    "5) dois projetos pequenos publicados. Depois escolha uma direção, como web, dados, mobile ou segurança. "
                    "Se me disser quanto tempo você tem por semana e o que deseja construir, eu organizo um plano de estudos realista.")
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
                goals=[g for g in (self.cloud.list_goals() or []) if not g.get("member_id") or str(g.get("member_id"))==str(self.active_member_id)]
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
                logger.warning("nex_goal_simulation_failed kind=%s", type(ex).__name__)
                return "Não consegui montar a simulação agora. Não vou inventar valores; tente novamente em instantes."

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
            return f"Seu mês está assim: entrou {brl(income)}, saíram {brl(expense)} já efetivados e o saldo atual do perfil está em {brl(balance)}. Há {brl(pending)} em compromissos futuros; depois deles, o projetado fica em {brl(projected)}.{extra}"

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
                all_rows=member_expense_rows(self.cloud.all_expenses_full(), self.active_member_id)
                rows=[r for r in all_rows if r.get("month") in months and expense_status(r) in ("paid","effective")]
                # Intervalo explícito dd/mm[/aaaa] a dd/mm[/aaaa]. Nunca presume datas ausentes.
                qn=self._norm(q)
                dates=re.findall(r"(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?", q)
                if len(dates)>=2:
                    def mkdate(t):
                        day,mon,yr=t; yr=int(yr) if yr else int(self.month[3:]); yr=yr+2000 if yr<100 else yr
                        return datetime(yr,int(mon),int(day)).date()
                    d1,d2=mkdate(dates[0]),mkdate(dates[1]); lo,hi=min(d1,d2),max(d1,d2)
                    rows=[r for r in all_rows if r.get("expense_date") and lo<=day(r["expense_date"])<=hi]
                # O chat financeiro sempre respeita o perfil ativo. Para consultar
                # outra pessoa, o usuário deve trocar o perfil no seletor visível.
                for m in self.members():
                    mn=self._norm(m.get("display_name"))
                    if mn and re.search(rf"\b{re.escape(mn)}\b", qn):
                        if str(m.get("id")) != str(self.active_member_id):
                            return f"Esta conversa está no perfil de {who}. Troque o perfil para consultar os dados de {m.get('display_name')}."
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
                logger.warning("nex_expense_lookup_failed kind=%s", type(ex).__name__)
                return "Não consegui consultar os lançamentos agora. Para evitar inventar dados, não vou estimar o resultado."

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
            acqs = self.active_member_acquisitions(True)
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
