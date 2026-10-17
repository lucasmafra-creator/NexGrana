import asyncio
import tempfile
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
os.environ["FLET_APP_STORAGE_DATA"] = str(Path(__file__).resolve().parent / "scratch" / "ui")

import flet as ft
from main import NexGranaCloud


class Page:
    def __init__(self, width=390):
        self.width = width
        self.height = 844
        self.controls = []
        self.services = []
        self.navigation_bar = None
        self.platform = "windows"
        self.dialogs = []

    def clean(self):
        self.controls.clear()

    def add(self, control):
        self.controls.append(control)

    def update(self):
        pass

    def show_dialog(self, control):
        self.dialogs.append(control)

    def pop_dialog(self):
        if self.dialogs:
            self.dialogs.pop()

    def run_task(self, handler, *args):
        result = handler if asyncio.iscoroutine(handler) else handler(*args)
        if asyncio.iscoroutine(result):
            return asyncio.run(result)
        return result


class FakeCloud:
    online = True

    def __init__(self):
        self.user = SimpleNamespace(id="user-a")
        self.household = {
            "id": "house-a",
            "mode": "family",
            "name": "Família teste",
            "invite_code": "test",
        }
        self.member = {
            "id": "mafra",
            "display_name": "Mafra",
            "user_id": "user-a",
            "role": "owner",
        }
        self.profile = {"full_name": "Mafra"}

    def _hid(self):
        return self.household["id"]

    def list_members(self):
        return [
            self.member,
            {
                "id": "karol",
                "display_name": "Karol",
                "user_id": None,
                "role": "member",
            },
        ]

    def all_income(self):
        return [
            {
                "id": "i",
                "amount": 1000,
                "member_id": "mafra",
                "received_at": "2026-09-01",
                "month": "09/2026",
                "note": "Teste",
            }
        ]

    def all_expenses_full(self):
        return [
            {
                "id": "e",
                "amount": 100,
                "payer_member_id": "mafra",
                "expense_date": "07/09/2026",
                "month": "09/2026",
                "description": "Conta",
                "category": "Outros",
                "kind": "Variável",
                "installments_total": 1,
                "installment_number": 1,
                "payment_status": "scheduled",
            }
        ]

    def all_expenses(self, **kwargs):
        return self.all_expenses_full()

    def list_income(self, month):
        return self.all_income()

    def list_expenses(self, month):
        return self.all_expenses_full()

    def list_goals(self):
        return [
            {
                "id": "g",
                "name": "Viagem",
                "target_amount": 300,
                "saved_amount": 0,
                "target_date": "2026-12-31",
                "status": "active",
                "strategy": "Equilibrada",
            }
        ]

    def list_acquisitions(self, *args):
        return [
            {
                "id": "a",
                "item": "Livro",
                "estimated": 50,
                "saved": 0,
                "priority": "Média",
                "member_id": "mafra",
                "status": "active",
            }
        ]

    def list_market_trips(self):
        return []

    def list_affiliate_offers(self):
        return []


class UITests(unittest.TestCase):
    def app(self, width=390):
        with patch.object(NexGranaCloud, "render_entry"):
            app = NexGranaCloud(Page(width))
        app.cloud = FakeCloud()
        app.month = "09/2026"
        return app

    def test_market_receipt_opt_in_posts_once_and_reports_pending(self):
        app=self.app(390);app.active_member_id='mafra'
        app.cloud.list_market_items=lambda _: [{'product_name':'QA arroz','quantity':2,'unit_price':3}]
        calls=[]
        app.cloud.finalize_market_expense=lambda *args: calls.append(args) or {'_sync_state':'pending'}
        app.cloud.finish_market_trip=lambda *args: self.fail('Must post only the selected financial flow')
        snacks=[];app.snack=lambda *args:snacks.append(args);app.render=lambda:None
        app.market_finish_dialog({'id':'trip','market_name':'QA','shopping_date':'2026-10-06'})
        dialog=app.page.dialogs[-1]
        next(c for c in self.controls(dialog.content) if isinstance(c,ft.TextField) and c.label=='Total da nota').value='7,00'
        next(c for c in self.controls(dialog.content) if isinstance(c,ft.Checkbox)).value=True
        dialog.actions[-1].on_click(None)
        confirm=app.page.dialogs[-1];confirm.actions[-1].on_click(None)
        confirm.actions[-1].on_click(None)
        self.assertEqual(len(calls),1);self.assertEqual(calls[0][-2:],('mafra','2026-10-06'))
        self.assertIn('aguardando sincronização',snacks[-1][0])

    def prepare_nex(self, app):
        app.screen = 3
        app.assistant_tab = 1
        app.chat_screen()

    def controls(self, root):
        yield root
        content=getattr(root,"content",None)
        if isinstance(content,ft.Control):
            yield from self.controls(content)
        for child in getattr(root,"controls",[]) or []:
            yield from self.controls(child)

    def by_data(self, root, value):
        return next(control for control in self.controls(root) if getattr(control,"data",None)==value)

    def test_home_labels_family_balance_and_keeps_individual_space_individual(self):
        app=self.app(390)
        family=[str(control.value) for control in self.controls(app.dashboard()) if isinstance(control,ft.Text)]
        self.assertIn("Saldo da família neste mês",family)
        self.assertIn("Saldos por integrante",family)
        self.assertIn("Saldo atual de Mafra neste mês",family)
        app.cloud.household["mode"]="individual"
        individual=[str(control.value) for control in self.controls(app.dashboard()) if isinstance(control,ft.Text)]
        self.assertNotIn("Saldo da família neste mês",individual)
        self.assertNotIn("Saldos por integrante",individual)

    def test_visual_styles_change_palette_and_keep_selection_in_account_preferences(self):
        app=self.app()
        with patch.object(app,"save_preferences") as save, patch.object(app,"render"):
            app.choose_visual_style("tech")
            self.assertEqual(app.preferences["visual_style"],"tech")
            self.assertEqual(app.page.bgcolor,"#0C111D")
            self.assertEqual(app.surface_color(),"#182235")
            self.assertEqual(app.border_color(),"#3A4B68")
            save.assert_called_once()
            app.choose_visual_style("claro")
            self.assertEqual(app.page.theme_mode,ft.ThemeMode.LIGHT)
            self.assertEqual(app.page.bgcolor,"#F4F6FC")
            with self.assertRaises(ValueError): app.choose_visual_style("unknown")

    def test_home_uses_standalone_nex_asset_and_appearance_previews(self):
        app=self.app(390)
        app.dashboard()
        self.assertIn(app.nex_idle_asset,{
            "nex/nex_welcome_v2.png","nex/nex_thinking_v2.png","nex/nex_celebrate_v2.png"
        })
        self.assertTrue((Path(__file__).resolve().parents[1] / "src" / "assets" / app.nex_idle_asset).is_file())
        self.assertEqual(len(app.appearance_previews().controls),3)

    def test_visual_style_is_scoped_by_account_and_space(self):
        app=self.app()
        rows={}
        class Vault:
            def read(self,key,default): return rows.get(key,default)
            def write(self,key,value): rows[key]=dict(value)
        app.cloud.vault=Vault()
        app.cloud._scope=lambda:app.cloud.user.id+":"+app.cloud.household["id"]
        with tempfile.TemporaryDirectory() as folder:
            app.preferences_path=Path(folder)/"preferences.json"
            app.preferences={"visual_style":"tech","dark_mode":True}
            app.save_preferences()
            app.cloud.user.id="user-b"
            self.assertNotIn("visual_style",app.load_preferences())
            app.cloud.user.id="user-a"
            self.assertEqual(app.load_preferences()["visual_style"],"tech")
            app.cloud.household["id"]="house-b"
            self.assertNotIn("visual_style",app.load_preferences())

    def test_acquisition_is_labeled_as_intention_not_a_goal(self):
        app=self.app(390)
        words=[str(control.value) for control in self.controls(app.acquisitions_screen()) if isinstance(control,ft.Text)]
        self.assertIn("Suas intenções de compra",words)
        self.assertIn("Aquisição é intenção de compra; não reserva dinheiro nem cria meta automaticamente.",words)
        self.assertTrue(any(value.startswith("Preço estimado:") for value in words))

    def test_list_items_error_is_not_presented_as_empty_list(self):
        app=self.app(390)
        app.cloud.list_shopping_lists=lambda:[{"id":"shopping-list","name":"Teste","budget":20}]
        app.cloud.list_shopping_list_items=lambda _id: (_ for _ in ()).throw(RuntimeError("offline"))
        words=[str(control.value) for control in self.controls(app._shopping_lists_panel()) if isinstance(control,ft.Text)]
        self.assertTrue(any(value.startswith("Itens indisponíveis:") for value in words))
        self.assertFalse(any("0 comprado(s)" in value for value in words))

    def test_all_screens_all_sizes(self):
        methods = (
            "dashboard",
            "income_screen",
            "expenses_screen",
            "acquisitions_screen",
            "market_screen",
            "planning_screen",
            "assistant_screen",
            "chat_screen",
            "extra_income_screen",
            "more_screen",
            "tutorial_screen",
        )
        for width in (360, 390, 430, 768, 1366, 1920):
            app = self.app(width)
            for method in methods:
                with self.subTest(width=width, screen=method):
                    self.assertIsInstance(getattr(app, method)(), ft.Control)

    def test_render_builds_and_reuses_safe_shell_for_every_main_route(self):
        app = self.app(390)
        app._members_cache = app.cloud.list_members()
        for screen in range(7):
            app.screen = screen
            app.render()
            self.assertIsNotNone(app.root_host)
            self.assertTrue(app.page.controls)

    def test_dialogs(self):
        app = self.app()
        dialogs = (
            ("income_dialog", ()),
            ("expense_dialog", ()),
            ("goal_dialog", ()),
            ("acq_dialog", ()),
            ("goal_edit_dialog", (app.cloud.list_goals()[0],)),
            ("payment_dialog", (app.cloud.all_expenses_full()[0],)),
            ("allocation_dialog", ()),
            ("simulate_entry_dialog", (app.cloud.list_goals()[0],)),
            ("analysis_dialog", ()),
            ("investment_simulator_dialog", ()),
            ("privacy_dialog", ()),
            ("nex_preferences_dialog", ()),
            ("nex_vivo_dialog", ()),
        )
        for method, args in dialogs:
            with self.subTest(dialog=method):
                getattr(app, method)(*args)

    def test_single_expense_label_does_not_call_it_an_installment(self):
        app=self.app()
        app.expense_dialog()
        dialog=app.page.dialogs[-1]
        fields=[c for c in dialog.content.controls if isinstance(c,ft.TextField)]
        self.assertIn("Valor da despesa",[f.label for f in fields])
        self.assertIn("Pagamento único: informe o valor da despesa.",
                      [c.value for c in dialog.content.controls if isinstance(c,ft.Text)])

    def test_android_entry_tutorial_and_market_forms_build(self):
        app=self.app(360)
        self.assertIsInstance(app.auth_screen(),ft.Control)
        self.assertIsInstance(app.workspace_screen(),ft.Control)
        app.market_item_dialog({'id':'trip-1'})
        app.tutorial_dialog()
        self.assertEqual(app.screen,6)
        self.assertIsInstance(app.tutorial_screen(),ft.Control)
        app.show_tutorial_offer(force=True)
        app.qa_reset_dialog()
        self.assertGreaterEqual(len(app.page.dialogs),3)

    def test_tutorial_activity_builds_in_every_module_and_screen_size(self):
        from services.tutorial import TUTORIAL_MODULES
        for width in (360,900):
            app=self.app(width)
            for module in TUTORIAL_MODULES:
                with self.subTest(width=width,module=module.key):
                    app.tutorial_session().current_module=module.key
                    self.assertIsInstance(app.tutorial_screen(),ft.Control)

    def test_tutorial_nex_is_multi_turn_chat(self):
        from services.tutorial import MODULE_BY_KEY
        app=self.app(360)
        session=app.tutorial_session()
        activity=app._tutorial_interactive_activity(MODULE_BY_KEY["nex"],session)
        field=next(c for c in self.controls(activity) if isinstance(c,ft.TextField))
        send=next(c for c in self.controls(activity) if isinstance(c,ft.Button) and c.content=="Enviar ao Nex de treino")
        with patch.object(field,"update"):
            field.value="opa bro"
            send.on_click(None)
            field.value="e uma despesa futura?"
            send.on_click(None)
        history=session.sandbox["nex"]["messages"]
        self.assertEqual([row["role"] for row in history],["assistant","user","assistant","user","assistant"])
        self.assertIn("vencimento",history[-1]["text"])
        self.assertTrue(any("opa bro" in c.value for c in self.controls(activity) if isinstance(c,ft.Text)))

    def test_tutorial_balance_is_fourth_and_explanatory(self):
        from services.tutorial import TUTORIAL_MODULES, MODULE_BY_KEY
        self.assertEqual([m.key for m in TUTORIAL_MODULES[:4]],["welcome","income","expense","balance"])
        app=self.app(390)
        activity=app._tutorial_balance_activity(app.tutorial_session())
        self.assertFalse(any(isinstance(c,ft.TextField) for c in self.controls(activity)))
        self.assertTrue(any("saldo projetado" in str(c.value).lower() for c in self.controls(activity) if isinstance(c,ft.Text)))
        app.tutorial_session().start("balance")
        nav=app._navigation_controls(MODULE_BY_KEY["balance"])
        labels=[str(c.content) for c in self.controls(nav) if isinstance(c,ft.Button)]
        self.assertIn("Concluir esta atividade",labels)

    def test_tutorial_completion_changes_advance_without_marking_done_step_skipped(self):
        from services.tutorial import MODULE_BY_KEY, TutorialStatus
        app=self.app(390)
        session=app.tutorial_session();session.start("nex")
        activity=app._tutorial_interactive_activity(MODULE_BY_KEY["nex"],session)
        app._navigation_controls(MODULE_BY_KEY["nex"])
        advance=app._tutorial_advance_button
        self.assertEqual(advance.content,"Pular esta atividade")
        question=next(c for c in self.controls(activity) if isinstance(c,ft.TextField))
        send=next(c for c in self.controls(activity) if isinstance(c,ft.Button) and c.content=="Enviar ao Nex de treino")
        with patch.object(question,"update"):
            question.value="oi"
            send.on_click(None)
        self.assertEqual(advance.content,"Próxima atividade")
        with patch.object(app,"render"):
            advance.on_click(None)
        self.assertEqual(session.statuses["nex"],TutorialStatus.COMPLETED.value)
        self.assertEqual(session.current_module,"family")

    def test_market_empty_desktop_stays_in_readable_width(self):
        app=self.app(1920)
        screen=app.market_screen()
        columns=[c for c in self.controls(screen) if isinstance(c,ft.Container) and c.width is not None]
        self.assertTrue(any(c.width==960 for c in columns))
        self.assertFalse(any(c.expand and c.bgcolor==ft.Colors.WHITE for c in columns))

    def test_market_list_fields_fit_mobile_without_expanded_row(self):
        app=self.app(360)
        app.cloud.list_shopping_lists=lambda:[{"id":"list-1","name":"Mês","budget":100}]
        app.cloud.list_shopping_list_items=lambda *_:[{"id":"item-1","name":"Arroz","quantity":1,"unit_price":20,"purchased":False}]
        screen=app.market_screen()
        self.assertTrue(any(isinstance(c,ft.Column) and c.scroll==ft.ScrollMode.AUTO for c in self.controls(screen)))
        fields=[c for c in self.controls(screen) if isinstance(c,ft.TextField)]
        self.assertGreaterEqual(len(fields),5)
        self.assertFalse(any(c.expand for c in fields))
        summary=[c.value for c in self.controls(screen) if isinstance(c,ft.Text) and "Gasto marcado" in str(c.value)]
        self.assertEqual(len(summary),1)
        self.assertIn("R$ 0,00",summary[0])
        self.assertIn("Restante após comprados",summary[0])

    def test_privacy_dialog_uses_theme_and_keeps_save_action(self):
        for width,height in ((360,800),(390,844),(412,915),(1366,768),(1920,1080)):
            app=self.app(width);app.page.height=height
            app.cloud.get_privacy_consents=lambda:{}
            app.privacy_dialog()
            dialog=app.page.dialogs[-1]
            self.assertEqual(dialog.bgcolor,app.surface_color())
            self.assertTrue(any(c.content=="Salvar preferências" for c in dialog.actions if isinstance(c,ft.Button)))
            self.assertLessEqual(dialog.content.height,height-100)

    def test_nex_chat_keeps_messages_and_composer_in_visible_structure(self):
        for width in (360,1366):
            app=self.app(width)
            app.chat_screen()
            app.chat_messages.extend([{"role":"user","text":"Primeira"},{"role":"assistant","text":"Resposta"}])
            app._persist_active_conversation()
            screen=app.chat_screen()
            live=next(c for c in self.controls(screen) if isinstance(c,ft.ListView) and c.expand)
            self.assertGreaterEqual(len(live.controls),3)
            self.assertTrue(any("Primeira" in str(c.value) for c in self.controls(live) if isinstance(c,ft.Text)))
            self.assertTrue(any(c.hint_text=="Fale com o Nex..." for c in self.controls(screen) if isinstance(c,ft.TextField)))
            self.assertTrue(any(isinstance(c,ft.Container) and c.content is live and c.bgcolor==app.page_color() for c in self.controls(screen)))

    def test_no_explicit_white_panel_in_dark_main_routes(self):
        app=self.app(390)
        app.preferences={"dark_mode":True,"visual_style":"original"}
        app.page.theme_mode=ft.ThemeMode.DARK
        for build in (app.dashboard,app.income_screen,app.expenses_screen,app.planning_screen,
                      app.market_screen,app.chat_screen,app.more_screen,app.tutorial_screen):
            with self.subTest(route=build.__name__):
                for control in self.controls(build()):
                    if isinstance(control,ft.Container):
                        self.assertNotIn(str(control.bgcolor).upper(),("#FFFFFF","WHITE"))

    def test_market_lists_and_achados_have_separate_responsive_surfaces(self):
        for width in (360,1200):
            app=self.app(width)
            app.cloud.list_shopping_lists=lambda:[{"id":"list-1","name":"Compra do mês","budget":900}]
            app.cloud.list_shopping_list_items=lambda *_:[
                {"id":"item-1","name":"Arroz","quantity":2,"unit_price":24.9,"purchased":False}]
            with self.subTest(width=width):
                purchases=app.market_screen()
                texts=[str(getattr(control,"value","") or "") for control in self.controls(purchases)]
                self.assertTrue(any("Restante após comprados" in value for value in texts))
                app._market_tab="Achados"
                offers=app.market_screen()
                self.assertIsInstance(offers,ft.Control)
                self.assertFalse(any("Restante estimado" in str(getattr(control,"value","") or "")
                                     for control in self.controls(offers)))

    def test_android_chat_keeps_exit_and_keyboard_close_without_sending(self):
        app=self.app(360)
        app.page.navigation_bar=ft.NavigationBar(destinations=[ft.NavigationBarDestination(icon=ft.Icons.HOME,label="Início")])
        screen=app.chat_screen()
        fields=[c for c in self.controls(screen) if isinstance(c,ft.TextField) and c.hint_text=="Fale com o Nex..."]
        self.assertEqual(len(fields),1)
        question=fields[0]
        close=self.by_data(screen,"nex-keyboard-close")
        question.value="rascunho sem enviar"
        question.on_focus(SimpleNamespace(control=question))
        self.assertTrue(close.visible)
        self.assertFalse(app.page.navigation_bar.visible)
        close.on_click(SimpleNamespace(control=close))
        self.assertEqual(app.nex_draft,"rascunho sem enviar")

    def test_auth_mode_switch_updates_fields_labels_and_selection(self):
        app=self.app(360)
        screen=app.auth_screen()
        login=self.by_data(screen,"auth-mode-login")
        signup=self.by_data(screen,"auth-mode-signup")
        submit=self.by_data(screen,"auth-submit")
        selected=self.by_data(screen,"auth-selected-mode")
        confirm=next(c for c in self.controls(screen) if isinstance(c,ft.TextField) and c.label=="Confirmar senha")

        self.assertFalse(confirm.visible)
        self.assertEqual(submit.content,"Entrar")
        self.assertIn("existente",selected.value)
        signup.on_click(None)
        self.assertTrue(confirm.visible)
        self.assertEqual(submit.content,"Criar conta")
        self.assertIn("nova",selected.value)
        self.assertEqual(signup.bgcolor,"#4658C9")
        login.on_click(None)
        self.assertFalse(confirm.visible)
        self.assertEqual(submit.content,"Entrar")
        self.assertEqual(login.bgcolor,"#4658C9")

    def test_auth_submit_executes_login_and_signup_without_name_error(self):
        app=self.app(360)
        app.workspace_screen=lambda: ft.Text("workspace")

        login_screen=app.auth_screen()
        login_fields={c.label:c for c in self.controls(login_screen) if isinstance(c,ft.TextField)}
        login_fields["E-mail"].value="exemplo-teste@example.invalid"
        login_fields["Senha"].value="senha-ficticia-123"
        login_calls=[]
        app.cloud.household=None
        app.cloud.sign_in=lambda email,password: (
            login_calls.append((email,password)) or SimpleNamespace(user=SimpleNamespace(id="user-a"))
        )
        asyncio.run(self.by_data(login_screen,"auth-submit").on_click(None))
        self.assertEqual(login_calls,[("exemplo-teste@example.invalid","senha-ficticia-123")])

        signup_screen=app.auth_screen()
        self.by_data(signup_screen,"auth-mode-signup").on_click(None)
        signup_fields={c.label:c for c in self.controls(signup_screen) if isinstance(c,ft.TextField)}
        signup_fields["E-mail"].value="nova@example.com"
        signup_fields["Senha"].value="segura123"
        signup_fields["Confirmar senha"].value="segura123"
        signup_calls=[]
        app.cloud.sign_up=lambda email,password,label: (
            signup_calls.append((email,password,label)) or SimpleNamespace(session=None,user=SimpleNamespace(id="user-b"))
        )
        asyncio.run(self.by_data(signup_screen,"auth-submit").on_click(None))
        self.assertEqual(signup_calls,[("nova@example.com","segura123","nova")])
        self.assertIn("Conta criada",self.by_data(signup_screen,"auth-status").value)

    def test_nex_action_has_response(self):
        app = self.app()
        self.prepare_nex(app)

        for text in (
            "bom dia",
            "Como está meu mês?",
            "qual aquisição de uns R$50 posso comprar?",
            "simular meta Viagem",
        ):
            before = len(app.chat_messages)
            accepted = app._process_nex_message(text)

            self.assertTrue(accepted)
            self.assertGreaterEqual(len(app.chat_messages), before + 2)

            reply = app.chat_messages[-1]
            self.assertEqual(reply["role"], "assistant")
            self.assertTrue(reply["text"])
            self.assertNotIn("Não consegui consultar", reply["text"])

    def test_no_invented_value_on_failure(self):
        app = self.app()
        self.prepare_nex(app)
        app.cloud.all_income = lambda: (_ for _ in ()).throw(ConnectionError())

        accepted = app._process_nex_message("Como está meu mês?")

        self.assertTrue(accepted)
        reply = app.chat_messages[-1]
        self.assertEqual(reply["role"], "assistant")
        self.assertIn("Não consegui consultar", reply["text"])
        self.assertNotIn("R$", reply["text"])

    def test_profile_scope_does_not_show_other_members_balance_or_bill(self):
        app = self.app()
        app._members_cache = app.cloud.list_members()
        app.active_member_id = "karol"
        data = app.dashboard_data()
        self.assertEqual(data["income"], 0)
        self.assertEqual(data["expense"], 0)
        self.assertEqual(data["pending_month"], 0)
        reply = app.nex_engine.respond(
            "Próximas contas",
            __import__("services.nex_engine", fromlist=["Context"]).Context(
                source="test", household_id="house-a", member_id="karol", month="09/2026", action="next_bills"
            ),
        )
        self.assertIn("Não encontrei", reply)
        self.assertNotIn("100", reply)

    def test_chat_has_free_conversation_and_at_most_five_pinned_per_person(self):
        app = self.app()
        app._members_cache = app.cloud.list_members()
        app.active_member_id = "mafra"
        app.chat_screen()
        for index in range(5):
            app.chat_messages.append({"role": "user", "text": f"Assunto {index}"})
            app._pin_free_conversation()
        self.assertEqual(len(app._read_chat_store()["pinned"]), 5)
        app.chat_messages.append({"role": "user", "text": "Sexto assunto"})
        app._pin_free_conversation()
        full_store = app._read_chat_store()
        self.assertEqual(len(full_store["pinned"]), 5)
        self.assertTrue(app.page.dialogs)
        replaced_id = full_store["pinned"][0]["id"]
        replaced_title = full_store["pinned"][0]["title"]
        app._pin_free_conversation(replace_id=replaced_id)
        full_store = app._read_chat_store()
        self.assertEqual(len(full_store["pinned"]), 5)
        self.assertEqual(len(full_store["archived"]), 1)
        self.assertEqual(full_store["archived"][0]["title"], replaced_title)
        self.assertIn("Sexto assunto", [row["title"] for row in full_store["pinned"]])
        self.assertEqual(full_store["free"]["messages"], [])
        app.active_member_id = "karol"
        app._loaded_chat_scope = None
        app.conversation_id = "free"
        self.assertEqual(len(app._read_chat_store()["pinned"]), 0)

    def test_free_chat_persistence_keeps_remote_identity(self):
        app = self.app()
        app._members_cache = app.cloud.list_members()
        app.active_member_id = "mafra"
        store = app._read_chat_store()
        store["free"] = {"messages": [], "remote_id": "remote-free-1"}
        app._write_chat_store(store)
        app.conversation_id = "free"
        app.chat_messages = [{"role": "user", "text": "Teste", "request_id": "request-1"}]
        app._persist_active_conversation()
        self.assertEqual(app._read_chat_store()["free"]["remote_id"], "remote-free-1")


if __name__ == "__main__":
    unittest.main()
