"""Painel web privado para administrar os Achados do NexGrana.

Execução local para homologação:
    py -m flet.cli run --web admin/achados_admin.py

O painel usa somente a chave pública do Supabase. A autorização efetiva é
feita por ``is_app_admin()`` e pelas políticas RLS; nunca use service_role no
navegador ou neste arquivo.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

import flet as ft
from supabase import create_client

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cloud import DEFAULT_SUPABASE_KEY, DEFAULT_SUPABASE_URL
from services.admin_offers import CATEGORIES, OfferValidationError, build_offer_payload, filter_admin_offers


LOGGER = logging.getLogger("nexgrana.admin.achados")
PURPLE = "#8B7CFF"
SURFACE = "#1B1E27"
CARD = "#222631"
MUTED = "#A9ADBA"


def field_values(fields: dict[str, ft.Control]) -> dict:
    """Extrai somente os campos permitidos; útil também para testes de UI."""
    return {key: getattr(control, "value", None) for key, control in fields.items()}


async def main(page: ft.Page):
    page.title = "NexGrana • Administração de Achados"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#101217"
    page.padding = 0
    page.scroll = None
    client = create_client(
        os.getenv("NEXGRANA_SUPABASE_URL", DEFAULT_SUPABASE_URL),
        os.getenv("NEXGRANA_SUPABASE_KEY", DEFAULT_SUPABASE_KEY),
    )
    state = {"user": None, "rows": []}
    cards_view = ft.ListView(expand=True, spacing=10)

    def message(text: str, error: bool = False):
        page.show_dialog(
            ft.SnackBar(ft.Text(text), bgcolor=ft.Colors.RED_700 if error else ft.Colors.GREEN_700)
        )

    def safe_failure(action: str, exc: Exception, public_text: str):
        LOGGER.warning("admin_offer_failed action=%s kind=%s", action, type(exc).__name__)
        message(public_text, True)

    async def sign_out(e=None):
        try:
            await asyncio.to_thread(client.auth.sign_out)
        except Exception as exc:
            LOGGER.info("admin_signout_failed kind=%s", type(exc).__name__)
        state["user"] = None
        render_login()

    def shell(title: str, body: ft.Control, actions=None):
        return ft.SafeArea(
            expand=True,
            content=ft.Column(
                expand=True,
                spacing=0,
                controls=[
                    ft.Container(
                        padding=16,
                        bgcolor="#181B23",
                        content=ft.Row(
                            controls=[
                                ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED, color=PURPLE),
                                ft.Column(
                                    expand=True,
                                    spacing=0,
                                    controls=[
                                        ft.Text(title, size=20, weight=ft.FontWeight.BOLD),
                                        ft.Text("Catálogo externo • protegido por login e RLS", size=10, color=MUTED),
                                    ],
                                ),
                                *(actions or []),
                            ]
                        ),
                    ),
                    ft.Container(expand=True, padding=16, content=body),
                ],
            ),
        )

    def preview_dialog(values: dict):
        image_url = str(values.get("image_url") or "").strip()
        visual = (
            ft.Image(src=image_url, width=180, height=140, fit=ft.BoxFit.COVER, border_radius=12)
            if image_url
            else ft.Container(
                width=180,
                height=140,
                border_radius=12,
                bgcolor="#171A22",
                alignment=ft.Alignment.CENTER,
                content=ft.Icon(ft.Icons.IMAGE_NOT_SUPPORTED_OUTLINED, size=42, color=MUTED),
            )
        )
        dialog = ft.AlertDialog(
            title=ft.Text("Prévia do achado"),
            content=ft.Column(
                width=460,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    visual,
                    ft.Text(str(values.get("title") or "Sem título"), size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(str(values.get("subtitle") or "Sem descrição"), color=MUTED),
                    ft.Text(f"{values.get('category') or 'Outros'} • Link de parceiro", size=11, color=PURPLE),
                    ft.Text("Preço e condições são confirmados no parceiro.", size=10, color=MUTED),
                ],
            ),
            actions=[ft.TextButton("Fechar", on_click=lambda e: page.pop_dialog())],
        )
        page.show_dialog(dialog)

    def offer_dialog(row=None):
        row = row or {}
        fields = {
            "title": ft.TextField(label="Título *", value=row.get("title") or "", max_length=180),
            "subtitle": ft.TextField(
                label="Descrição curta", value=row.get("subtitle") or "", multiline=True, min_lines=2, max_lines=4
            ),
            "provider": ft.TextField(label="Parceiro", value=row.get("provider") or "Mercado Livre"),
            "url": ft.TextField(label="Link afiliado HTTPS *", value=row.get("url") or ""),
            "image_url": ft.TextField(label="URL da imagem (http2.mlstatic.com)", value=row.get("image_url") or ""),
            "image_alt": ft.TextField(label="Descrição acessível da imagem", value=row.get("image_alt") or ""),
            "category": ft.Dropdown(
                label="Categoria *",
                value=row.get("category") if row.get("category") in CATEGORIES else "Outros",
                options=[ft.DropdownOption(item) for item in CATEGORIES],
            ),
            "search_tags": ft.TextField(
                label="Pesquisa: termos separados por vírgula", value=", ".join(row.get("search_tags") or [])
            ),
            "price": ft.TextField(
                label="Preço verificado (opcional)",
                value="" if row.get("price") is None else str(row.get("price")),
                keyboard_type=ft.KeyboardType.NUMBER,
            ),
            "sort_order": ft.TextField(
                label="Ordem", value=str(row.get("sort_order") if row.get("sort_order") is not None else 1000),
                keyboard_type=ft.KeyboardType.NUMBER,
            ),
            "expires_at": ft.TextField(
                label="Validade em UTC *", value=row.get("expires_at") or "2099-12-31T23:59:59Z"
            ),
            "enabled": ft.Switch(label="Publicado no aplicativo", value=bool(row.get("enabled", False))),
        }
        status = ft.Text("", visible=False, color=ft.Colors.RED_300)
        save_button = ft.Button("Salvar achado", icon=ft.Icons.SAVE_OUTLINED)
        width = max(300, min(660, float(page.width or 660) - 36))
        height = max(380, min(660, float(page.height or 800) - 160))
        dialog = ft.AlertDialog(
            title=ft.Text("Editar achado" if row else "Novo achado"),
            content=ft.Column(
                width=width,
                height=height,
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    ft.Text("Os campos com * são obrigatórios. Nada é publicado sem sua confirmação.", size=11, color=MUTED),
                    fields["title"], fields["subtitle"], fields["provider"], fields["url"],
                    fields["image_url"], fields["image_alt"], fields["category"], fields["search_tags"],
                    ft.ResponsiveRow(
                        controls=[
                            ft.Container(col={"xs": 12, "md": 6}, content=fields["price"]),
                            ft.Container(col={"xs": 12, "md": 6}, content=fields["sort_order"]),
                        ]
                    ),
                    fields["expires_at"], fields["enabled"],
                    ft.Text(
                        "Preço é opcional. Se não houver fonte confiável, deixe vazio: o app nunca inventa valores.",
                        size=10,
                        color=MUTED,
                    ),
                    status,
                ],
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()),
                ft.TextButton("Visualizar", icon=ft.Icons.VISIBILITY_OUTLINED, on_click=lambda e: preview_dialog(field_values(fields))),
                save_button,
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        async def save(e):
            try:
                payload = build_offer_payload(field_values(fields), existing=row)
            except OfferValidationError as exc:
                status.value = str(exc)
                status.visible = True
                page.update()
                return
            save_button.disabled = True
            status.value = "Salvando e registrando auditoria…"
            status.color = MUTED
            status.visible = True
            page.update()
            try:
                if row.get("id"):
                    await asyncio.to_thread(
                        lambda: client.table("affiliate_offers").update(payload).eq("id", row["id"]).execute()
                    )
                else:
                    await asyncio.to_thread(lambda: client.table("affiliate_offers").insert(payload).execute())
                page.pop_dialog()
                message("Achado salvo com sucesso e registrado na auditoria.")
                await render_catalog()
            except Exception as exc:
                save_button.disabled = False
                status.value = "Não foi possível salvar. Confira a migração 0.22 e sua permissão administrativa."
                status.color = ft.Colors.RED_300
                page.update()
                safe_failure("save", exc, "O banco recusou a alteração; nenhum dado parcial foi publicado.")

        save_button.on_click = save
        page.show_dialog(dialog)

    def confirm_delete(row: dict):
        delete_button = ft.Button("Excluir definitivamente", icon=ft.Icons.DELETE_FOREVER_OUTLINED)
        dialog = ft.AlertDialog(
            title=ft.Text("Excluir achado?"),
            content=ft.Text(
                f"“{row.get('title') or 'Sem título'}” será removido. A exclusão fica registrada na auditoria."
            ),
            actions=[ft.TextButton("Cancelar", on_click=lambda e: page.pop_dialog()), delete_button],
        )

        async def remove(e):
            delete_button.disabled = True
            page.update()
            try:
                await asyncio.to_thread(
                    lambda: client.table("affiliate_offers").delete().eq("id", row["id"]).execute()
                )
                page.pop_dialog()
                message("Achado excluído; a auditoria foi preservada.")
                await render_catalog()
            except Exception as exc:
                delete_button.disabled = False
                page.update()
                safe_failure("delete", exc, "Não foi possível excluir. Confira sua permissão.")

        delete_button.on_click = remove
        page.show_dialog(dialog)

    async def toggle_offer(row: dict):
        target = not bool(row.get("enabled"))
        try:
            await asyncio.to_thread(
                lambda: client.table("affiliate_offers").update({"enabled": target}).eq("id", row["id"]).execute()
            )
            message("Achado publicado." if target else "Achado retirado do aplicativo.")
            await render_catalog()
        except Exception as exc:
            safe_failure(
                "toggle", exc,
                "Não foi possível alterar a publicação. Verifique a validade do achado e sua permissão.",
            )

    def offer_card(row: dict) -> ft.Control:
        published = bool(row.get("enabled"))
        image_url = row.get("image_url")
        image = (
            ft.Image(src=image_url, width=88, height=72, fit=ft.BoxFit.COVER, border_radius=10)
            if image_url
            else ft.Container(
                width=88, height=72, border_radius=10, bgcolor="#171A22", alignment=ft.Alignment.CENTER,
                content=ft.Icon(ft.Icons.SELL_OUTLINED, color=PURPLE),
            )
        )
        details = ft.Column(
            expand=True,
            spacing=3,
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(row.get("title") or "Sem título", weight=ft.FontWeight.BOLD, expand=True),
                        ft.Container(
                            padding=ft.Padding.symmetric(horizontal=8, vertical=3), border_radius=20,
                            bgcolor="#173D2B" if published else "#343743",
                            content=ft.Text("Publicado" if published else "Rascunho", size=9),
                        ),
                    ]
                ),
                ft.Text(f"{row.get('category', 'Outros')} • {row.get('provider', 'Parceiro')}", size=10, color=MUTED),
                ft.Text(row.get("subtitle") or "Sem descrição curta", size=11, color=MUTED, max_lines=2),
                ft.Text(row.get("url") or "", size=9, selectable=True, color=PURPLE, max_lines=1),
            ],
        )
        actions = ft.Row(
            wrap=True,
            spacing=4,
            controls=[
                ft.TextButton("Prévia", icon=ft.Icons.VISIBILITY_OUTLINED, on_click=lambda e: preview_dialog(row)),
                ft.TextButton("Editar", icon=ft.Icons.EDIT_OUTLINED, on_click=lambda e: offer_dialog(row)),
                ft.TextButton(
                    "Desativar" if published else "Publicar",
                    icon=ft.Icons.UNPUBLISHED_OUTLINED if published else ft.Icons.PUBLISH_OUTLINED,
                    on_click=lambda e: toggle_offer(row),
                ),
                ft.IconButton(
                    ft.Icons.DELETE_OUTLINE, tooltip="Excluir", icon_color=ft.Colors.RED_300,
                    on_click=lambda e: confirm_delete(row),
                ),
            ],
        )
        return ft.Container(
            padding=14,
            border_radius=14,
            bgcolor=CARD,
            content=ft.Column(
                spacing=8,
                controls=[ft.Row(vertical_alignment=ft.CrossAxisAlignment.START, controls=[image, details]), actions],
            ),
        )

    def refresh_cards(query: str = "", status: str = "all", category: str = "all"):
        visible = filter_admin_offers(state["rows"], query, status, category)
        cards_view.controls = [offer_card(row) for row in visible]
        if not visible:
            cards_view.controls = [
                ft.Container(
                    padding=30,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(ft.Icons.SEARCH_OFF_OUTLINED, size=42, color=MUTED),
                            ft.Text("Nenhum achado corresponde aos filtros."),
                        ],
                    ),
                )
            ]
        page.update()

    async def render_catalog():
        try:
            response = await asyncio.to_thread(
                lambda: client.table("affiliate_offers").select("*").order("sort_order").execute()
            )
            state["rows"] = response.data or []
        except Exception as exc:
            safe_failure("load", exc, "Não foi possível carregar o catálogo. Confira conexão, migração e permissão.")
            return

        search = ft.TextField(label="Pesquisar", prefix_icon=ft.Icons.SEARCH, expand=True)
        status_filter = ft.Dropdown(
            label="Status", value="all", width=170,
            options=[
                ft.DropdownOption(key="all", text="Todos"),
                ft.DropdownOption(key="published", text="Publicados"),
                ft.DropdownOption(key="draft", text="Rascunhos"),
            ],
        )
        category_filter = ft.Dropdown(
            label="Categoria", value="all", width=220,
            options=[ft.DropdownOption(key="all", text="Todas"), *[ft.DropdownOption(item) for item in CATEGORIES]],
        )

        def changed(e=None):
            refresh_cards(search.value, status_filter.value, category_filter.value)

        search.on_change = changed
        status_filter.on_select = changed
        category_filter.on_select = changed
        refresh_cards()
        total = len(state["rows"])
        published = sum(1 for row in state["rows"] if row.get("enabled"))
        body = ft.Column(
            expand=True,
            controls=[
                ft.ResponsiveRow(
                    controls=[
                        ft.Container(col={"xs": 12, "md": 6}, content=search),
                        ft.Container(col={"xs": 6, "md": 3}, content=status_filter),
                        ft.Container(col={"xs": 6, "md": 3}, content=category_filter),
                    ]
                ),
                ft.Row(
                    controls=[
                        ft.Text(f"{total} no catálogo • {published} publicados", size=11, color=MUTED, expand=True),
                        ft.Icon(ft.Icons.VERIFIED_USER_OUTLINED, size=16, color=ft.Colors.GREEN_400),
                        ft.Text("RLS e auditoria ativos", size=10, color=ft.Colors.GREEN_300),
                    ]
                ),
                cards_view,
            ],
        )
        page.clean()
        page.add(
            shell(
                "Administração de Achados", body,
                [
                    ft.Button("Novo", icon=ft.Icons.ADD, on_click=lambda e: offer_dialog()),
                    ft.IconButton(ft.Icons.REFRESH, tooltip="Atualizar", on_click=lambda e: render_catalog()),
                    ft.IconButton(ft.Icons.LOGOUT, tooltip="Sair", on_click=sign_out),
                ],
            )
        )
        page.update()

    def render_login():
        email = ft.TextField(label="E-mail administrativo", keyboard_type=ft.KeyboardType.EMAIL, width=420)
        password = ft.TextField(label="Senha", password=True, can_reveal_password=True, width=420)
        button = ft.Button("Entrar no painel", icon=ft.Icons.LOGIN)
        status = ft.Text("", visible=False, color=ft.Colors.RED_300)

        async def login(e):
            if not str(email.value or "").strip() or not password.value:
                status.value = "Informe e-mail e senha."
                status.visible = True
                page.update()
                return
            button.disabled = True
            status.value = "Validando conta e permissão…"
            status.color = MUTED
            status.visible = True
            page.update()
            try:
                result = await asyncio.to_thread(
                    lambda: client.auth.sign_in_with_password({"email": email.value.strip(), "password": password.value})
                )
                allowed = await asyncio.to_thread(lambda: client.rpc("is_app_admin").execute().data)
                if not result.user or not allowed:
                    await asyncio.to_thread(client.auth.sign_out)
                    raise PermissionError()
                state["user"] = result.user
                await render_catalog()
            except Exception as exc:
                LOGGER.warning("admin_login_failed kind=%s", type(exc).__name__)
                status.value = "Acesso negado. Use uma conta explicitamente autorizada em app_admins."
                status.color = ft.Colors.RED_300
                status.visible = True
                button.disabled = False
                page.update()

        button.on_click = login
        page.clean()
        page.add(
            shell(
                "NexGrana • painel privado",
                ft.Container(
                    alignment=ft.Alignment.CENTER,
                    content=ft.Container(
                        width=500, padding=24, bgcolor=SURFACE, border_radius=20,
                        content=ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Icon(ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED, size=52, color=PURPLE),
                                ft.Text("Gerencie os links exibidos em Achados", size=20, weight=ft.FontWeight.BOLD),
                                ft.Text(
                                    "Somente Lucas e administradores explicitamente autorizados.",
                                    text_align=ft.TextAlign.CENTER, color=MUTED,
                                ),
                                email, password, status, button,
                                ft.Text(
                                    "A autorização é validada no banco. O painel nunca usa service_role.",
                                    size=10, color=MUTED,
                                ),
                            ],
                        ),
                    ),
                ),
            )
        )
        page.update()

    render_login()


if __name__ == "__main__":
    ft.run(main)
