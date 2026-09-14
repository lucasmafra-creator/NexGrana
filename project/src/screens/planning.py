from ui.common import brl, date, datetime, ft, goal_scenarios, money, parse_date, uuid

class PlanningScreen:
    def goal_edit_dialog(self, row):
        name=ft.TextField(label="Nome da meta",value=row.get("name") or "")
        target=ft.TextField(label="Valor objetivo",value=str(row.get("target_amount") or 0).replace(".",","),keyboard_type=ft.KeyboardType.NUMBER)
        saved=ft.TextField(label="Já guardado",value=str(row.get("saved_amount") or 0).replace(".",","),disabled=True,helper="Use ‘Aportar’ para preservar o histórico e evitar conflito entre integrantes.")
        raw=str(row.get("target_date") or "")
        try:
            dt=datetime.fromisoformat(raw[:10]).strftime("%d/%m/%Y")
        except Exception:
            dt=raw
        deadline=ft.TextField(label="Data final",value=dt,hint_text="dd/mm/aaaa")
        strategy=ft.Dropdown(label="Estratégia",value=row.get("strategy") or "Equilibrada",options=[ft.DropdownOption(x) for x in ["Confortável","Equilibrada","Agressiva","Personalizada"]])
        owner=ft.Dropdown(label="Responsável",options=self.member_options(),value=row.get("member_id"))
        status=ft.Dropdown(label="Status",value=row.get("status","active"),options=[ft.DropdownOption(key=k,text=v) for k,v in [("active","Ativa"),("paused","Pausada"),("completed","Concluída"),("cancelled","Cancelada")]])
        d=ft.AlertDialog(title=ft.Text("Editar meta"),content=ft.Column(width=500,tight=True,scroll=ft.ScrollMode.AUTO,controls=[name,target,saved,deadline,strategy,owner,status]))
        def save(e):
            try:
                dt2=parse_date(deadline.value)
                self.cloud.update_goal(row["id"],expected_version=int(row.get("version") or 0),name=name.value.strip(),target_amount=money(target.value),target_date=dt2.date().isoformat(),strategy=strategy.value,member_id=owner.value,status=status.value)
                self.page.pop_dialog(); self.render(); self.snack("Meta atualizada e planejamento recalculado.")
            except Exception as ex:self.snack(f"Não foi possível editar a meta: {ex}",True)
        d.actions=[ft.TextButton("Cancelar",on_click=lambda e:self.page.pop_dialog()),ft.Button("Salvar alterações",on_click=save)]
        self.page.show_dialog(d)


    def planning_screen(self):
        try:
            goals=self.cloud.list_goals()
        except Exception:
            goals=[]
        active=[g for g in goals if str(g.get("status") or "active") in ("active","paused")]
        data=self.dashboard_data()
        total_target=sum(float(g.get("target_amount") or 0) for g in active)
        total_saved=sum(float(g.get("saved_amount") or 0) for g in active)
        remaining=max(total_target-total_saved,0)
        cards=[]
        for g in active:
            target=float(g.get("target_amount") or 0); saved=float(g.get("saved_amount") or 0); rem=max(target-saved,0)
            pct=min(saved/max(target,1),1)
            try:
                deadline=datetime.fromisoformat(str(g.get("target_date"))[:10]).date()
            except Exception:
                deadline=date.today()
            months=max(1,(deadline.year-date.today().year)*12+deadline.month-date.today().month+1)
            scenario=goal_scenarios(g,data.get("projected_monthly_result",0),data.get("projected_balance",0),goals,today=date.today(),reserve=self.preferences.get("minimum_reserve",0))
            monthly=scenario["keep"]
            free=scenario["free"]
            if pct>=1:
                status="Concluída"; color=ft.Colors.GREEN; mood="celebrate"
            elif monthly<=free*0.75:
                status="No caminho"; color=ft.Colors.GREEN; mood="idle"
            elif monthly<=free:
                status="Atenção"; color=ft.Colors.ORANGE; mood="thinking"
            else:
                status="Exige ajuste"; color=ft.Colors.ORANGE; mood="worry"
            cards.append(ft.Container(
                padding=15,bgcolor=self.surface_color(),border_radius=18,border=ft.Border.all(1,self.border_color()),
                content=ft.Column(spacing=9,controls=[
                    ft.Row(vertical_alignment=ft.CrossAxisAlignment.START,controls=[
                        ft.Container(width=54,height=54,border_radius=15,bgcolor="#151A2E",alignment=ft.Alignment.CENTER,content=ft.Icon(self._acquisition_icon(g.get("name","")),color="#8B7CFF",size=28)),
                        ft.Column(expand=True,spacing=2,controls=[
                            ft.Text(g.get("name") or "Meta",size=18,weight=ft.FontWeight.BOLD),
                            ft.Text(f"Até {deadline.strftime('%d/%m/%Y')} • {g.get('strategy','Equilibrada')}",size=10,color=self.muted_color()),
                        ]),
                        ft.Container(padding=ft.Padding.symmetric(horizontal=10,vertical=5),border_radius=20,bgcolor=ft.Colors.with_opacity(0.12,color),content=ft.Text(status,size=10,color=color,weight=ft.FontWeight.BOLD))
                    ]),
                    ft.ProgressBar(value=pct,color=color),
                    ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN,controls=[
                        ft.Text(f"{brl(saved)} de {brl(target)}",size=11),
                        ft.Text(f"{int(pct*100)}%",size=11,weight=ft.FontWeight.BOLD)
                    ]),
                    ft.Text(f"Para manter o prazo: {brl(monthly)}/mês pelos próximos {months} mês(es).",weight=ft.FontWeight.BOLD),
                    ft.Container(padding=10,border_radius=13,bgcolor="#17192B",content=ft.Row(controls=[
                        ft.Image(src=self.nex_asset(mood,"avatar"),width=62,height=62,fit=ft.BoxFit.CONTAIN),
                        ft.Text(("Essa meta cabe na margem atual." if monthly<=free else f"Hoje a margem projetada é {brl(free)}. Podemos alongar o prazo ou reduzir o valor mensal."),size=10,color=self.muted_color(),expand=True)
                    ])),
                    ft.Row(wrap=True,controls=[
                        ft.Button("Aportar",icon=ft.Icons.ADD_CARD,on_click=lambda e,row=g:self.goal_contribution_dialog(row)),
                        ft.OutlinedButton("Editar",icon=ft.Icons.EDIT_OUTLINED,on_click=lambda e,row=g:self.goal_edit_dialog(row)),
                        ft.OutlinedButton("Simular aporte",on_click=lambda e,row=g:self.simulate_entry_dialog(row)),
                        ft.OutlinedButton("Simular com Nex",icon=ft.Icons.AUTO_AWESOME,on_click=lambda e,name=g.get("name","meta"),gid=g.get("id"):self._start_nex_topic(f"Quero simular alternativas para a meta {name}. Considere meu orçamento atual.",source="planning",entity_id=gid,action="simulate_goal")),
                        ft.TextButton("Excluir",icon=ft.Icons.DELETE_OUTLINE,on_click=lambda e,rid=g["id"]:self.delete_goal(rid)),
                    ])
                ])
            ))
        summary=ft.ResponsiveRow(spacing=8,run_spacing=8,controls=[
            self._mini_stat("Metas ativas",str(len(active)),ft.Icons.TRACK_CHANGES,"#8B7CFF","objetivos"),
            self._mini_stat("Já guardado",brl(total_saved),ft.Icons.SAVINGS_OUTLINED,ft.Colors.GREEN,"nas metas"),
            self._mini_stat("Falta juntar",brl(remaining),ft.Icons.HOURGLASS_BOTTOM,ft.Colors.ORANGE,"total"),
        ])
        return ft.Column(expand=True,controls=[
            self.header("Planejamento","Metas vivas, recalculadas conforme sua realidade"),
            ft.Container(padding=16,expand=True,content=ft.Column(scroll=ft.ScrollMode.ALWAYS,spacing=12,controls=[
                summary,
                ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN,controls=[
                    ft.Text("Objetivos financeiros",size=18,weight=ft.FontWeight.BOLD),
                    ft.Button("Nova meta",icon=ft.Icons.ADD,on_click=self.goal_dialog),
                ]),
                ft.Text("O NexGrana recalcula o esforço mensal conforme aportes, prazo e margem projetada. Ele orienta; não movimenta dinheiro automaticamente.",size=10,color=self.muted_color()),
                *(cards if cards else [ft.Container(padding=24,content=ft.Text("Nenhuma meta ativa. Crie uma para transformar um objetivo em plano.",color=self.muted_color()))]),
            ]))
        ])


    def goal_dialog(self, e=None, prefill=None):
        name=ft.TextField(label="Nome da meta",hint_text="Ex.: Viagem",value=(prefill or {}).get("item","") if isinstance(prefill,dict) else "")
        target=ft.TextField(label="Valor objetivo",keyboard_type=ft.KeyboardType.NUMBER,value=(str((prefill or {}).get("estimated") or "").replace(".",",") if isinstance(prefill,dict) else ""))
        saved=ft.TextField(label="Já guardado",value=(str((prefill or {}).get("saved") or 0).replace(".",",") if isinstance(prefill,dict) else "0"),keyboard_type=ft.KeyboardType.NUMBER)
        deadline=ft.TextField(label="Data final",hint_text="dd/mm/aaaa")
        strategy=ft.Dropdown(label="Estratégia",value="Equilibrada",options=[ft.DropdownOption(x) for x in ["Confortável","Equilibrada","Agressiva","Personalizada"]])
        acqs=self.cloud.list_acquisitions(True)
        acq_map={str(a["id"]):a for a in acqs}
        import_acq=ft.Dropdown(label="Importar de Aquisições (opcional)",options=[ft.DropdownOption(key=str(a["id"]),text=f"{a.get('item','Item')} • {brl(a.get('estimated',0))}") for a in acqs])
        analysis=ft.Text("O NexGrana vai comparar a meta com sua margem e compromissos reais.",size=10,color=self.muted_color())
        def import_change(e):
            row=acq_map.get(str(import_acq.value))
            if row:
                name.value=row.get("item") or "";target.value=str(row.get("estimated") or 0).replace(".",",");saved.value=str(row.get("saved") or 0).replace(".",",");self.page.update()
        import_acq.on_select=import_change
        d=ft.AlertDialog(title=ft.Text("Nova meta"),content=ft.Column(width=520,tight=True,controls=[import_acq,name,target,saved,deadline,strategy,analysis]))
        def save(e):
            try:
                dt=parse_date(deadline.value);target_v=money(target.value);saved_v=money(saved.value)
                if target_v<=0:raise ValueError("Informe um valor objetivo maior que zero.")
                months=max(1,(dt.year-date.today().year)*12+dt.month-date.today().month+1)
                monthly=max(0,(target_v-saved_v)/months);free=max(0,float(self.dashboard_data().get("projected_balance") or 0))
                self.cloud.add_goal(name.value,target_v,saved_v,dt.date().isoformat(),strategy.value,member_id=(self.active_member() or {}).get("id"),acquisition_id=import_acq.value or (prefill or {}).get("id"))
                self.page.pop_dialog();self.render()
                self.snack(f"Meta criada. Referência: {brl(monthly)}/mês." + (f" A margem projetada atual é {brl(free)}." if monthly>free else " Está dentro da margem atual."))
            except Exception as ex:self.snack(f"Não foi possível criar a meta: {ex}",True)
        d.actions=[ft.TextButton("Cancelar",on_click=lambda e:self.page.pop_dialog()),ft.Button("Criar meta",on_click=save)]
        self.page.show_dialog(d)


    def goal_contribution_dialog(self, row):
        value = ft.TextField(label="Valor guardado agora", keyboard_type=ft.KeyboardType.NUMBER)
        dialog=ft.AlertDialog(title=ft.Text(f"Aporte — {row['name']}"), content=value)
        operation_id=str(uuid.uuid4())
        def save(e):
            try:
                contribution=money(value.value)
                if contribution<=0:raise ValueError("Aporte deve ser positivo.")
                self.cloud.client.rpc('contribute_goal',{'p_goal':row['id'],'p_amount':contribution,'p_id':operation_id}).execute()
                self.page.pop_dialog(); self.render()
            except Exception as ex: self.snack(str(ex), True)
        dialog.actions=[ft.TextButton("Cancelar", on_click=lambda e:self.page.pop_dialog()), ft.Button("Salvar aporte", on_click=save)]
        self.page.show_dialog(dialog)


    def delete_goal(self, rid):
        try:
            self.cloud.delete_goal(rid); self.render()
        except Exception as ex: self.snack(str(ex), True)


    def simulate_entry_dialog(self,row):
        entry=ft.TextField(label='Aporte agora (simulação)',value='0')
        result=ft.Text('',selectable=True)
        d=ft.AlertDialog(title=ft.Text('Simular aporte'),content=ft.Column(tight=True,controls=[entry,result]))
        def simulate(e):
            try:
                data=self.dashboard_data()
                scenario=goal_scenarios(row,data['projected_monthly_result'],data['projected_balance'],self.cloud.list_goals(),money(entry.value),reserve=self.preferences.get('minimum_reserve',0))
                result.value=f"Após aporte: {brl(scenario['after_entry'])}/mês; saldo projetado {brl(scenario['projected_after_entry'])}. Outras metas pedem {brl(scenario['other_goals'])}/mês. Simulação, sem movimentar dinheiro."
                d.update()
            except ValueError as exc:self.snack(str(exc),True)
        d.actions=[ft.TextButton('Fechar',on_click=lambda e:self.page.pop_dialog()),ft.Button('Simular',on_click=simulate)]
        self.page.show_dialog(d)


