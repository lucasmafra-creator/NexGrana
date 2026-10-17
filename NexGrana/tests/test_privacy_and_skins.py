import unittest
from datetime import date
from pathlib import Path
from PIL import Image
from types import SimpleNamespace

from services.nex_skins import _CATALOG, occasion_skin, preview_asset, selected_skin, skin_asset
from services.privacy import export_snapshot


class PrivacyAndSkinsTests(unittest.TestCase):
    def test_manual_skin_overrides_december_and_auto_returns(self):
        self.assertEqual(selected_skin({}, date(2026, 12, 1)), 'winter')
        self.assertIsNone(skin_asset({}, date(2026, 9, 30)))
        self.assertEqual(selected_skin({'nex_skin': 'original'}, date(2026, 12, 1)), 'original')

    def test_occasions_include_festive_and_social_awareness_art(self):
        self.assertEqual(occasion_skin(date(2026, 2, 14)), 'carnaval')
        self.assertEqual(occasion_skin(date(2026, 4, 5)), 'pascoa')
        self.assertEqual(occasion_skin(date(2026, 3, 8)), 'dia_da_mulher')
        self.assertEqual(occasion_skin(date(2026, 4, 19)), 'povos_indigenas')
        self.assertEqual(occasion_skin(date(2026, 5, 1)), 'trabalho')
        self.assertEqual(occasion_skin(date(2026, 6, 5)), 'meio_ambiente')
        self.assertEqual(occasion_skin(date(2026, 10, 31)), 'halloween')
        self.assertEqual(occasion_skin(date(2026, 11, 20)), 'consciencia_negra')
        self.assertEqual(occasion_skin(date(2026, 12, 24)), 'natal')

    def test_manual_skin_is_available_and_transparent_variants_fit_roles(self):
        manual={'nex_skin':'povos_indigenas'}
        self.assertEqual(selected_skin(manual, date(2026, 8, 2)), 'povos_indigenas')
        full='nex/skins/cutouts/povos_indigenas_v3.png'
        small='nex/skins/cutouts/povos_indigenas_avatar_v3.png'
        self.assertEqual(preview_asset('povos_indigenas'), full)
        for role in ('avatar', 'compact', 'dock'):
            self.assertEqual(skin_asset(manual, role=role), small)
        for role in ('card', 'hero'):
            self.assertEqual(skin_asset(manual, role=role), full)

    def test_automatic_social_and_festive_skins_require_explicit_allowlist(self):
        self.assertIsNone(skin_asset({}, date(2026, 11, 20), role='hero'))
        self.assertEqual(
            skin_asset({'nex_auto_allowed_skins':['consciencia_negra']}, date(2026, 11, 20), role='hero'),
            'nex/skins/cutouts/consciencia_negra_v3.png',
        )

    def test_contextual_skin_requires_auto_opt_in_and_exact_allowlist(self):
        date_neutral=date(2026, 9, 30)
        self.assertIsNone(skin_asset({'nex_context_auto':True,'nex_auto_allowed_skins':['investidor']},date_neutral,role='hero',context='market'))
        self.assertEqual(
            skin_asset({'nex_context_auto':True,'nex_auto_allowed_skins':['compras']},date_neutral,role='hero',context='market'),
            'nex/skins/cutouts/compras_v3.png',
        )
        self.assertIsNone(skin_asset({'nex_auto_allowed_skins':['compras']},date_neutral,role='hero',context='market'))

    def test_manual_skin_is_not_overridden_by_context(self):
        preferences={'nex_skin':'original','nex_context_auto':True,'nex_auto_allowed_skins':['investidor']}
        self.assertEqual(skin_asset(preferences,date(2026, 9, 30),role='hero',context='investments'),'nex/nex_hd.png')

    def test_every_outfit_has_padded_transparent_full_and_compact_assets(self):
        assets=Path(__file__).resolve().parents[1]/'src/assets'
        self.assertEqual(len(_CATALOG), 36)
        for key in _CATALOG:
            for role, size in (('hero',768),('avatar',128)):
                with self.subTest(key=key,role=role):
                    with Image.open(assets/skin_asset({'nex_skin':key},role=role)) as image:
                        self.assertEqual(image.mode, 'RGBA')
                        self.assertEqual(image.size, (size,size))
                        alpha=image.getchannel('A')
                        self.assertEqual(alpha.getextrema(), (0,255))
                        box=alpha.getbbox()
                        self.assertGreater(box[0],0)
                        self.assertGreater(box[1],0)
                        self.assertLess(box[2],size)
                        self.assertLess(box[3],size)

    def test_export_includes_lists_but_only_own_private_chat(self):
        class CloudStub:
            user=SimpleNamespace(id='mine')
            household={'id': 'space'}
            def list_members(self): return [{'id': 'member'}]
            def all_expenses_full(self): return [{'expense_shares': [{'id': 'share'}]}]
            def fetch_all(self, table):
                if table == 'nex_messages':
                    return [{'owner_user_id': 'mine'}, {'owner_user_id': 'other'}]
                if table == 'nex_conversations':
                    return [{'owner_user_id': 'mine'}, {'owner_user_id': 'other'}]
                return []
        data=export_snapshot(CloudStub())
        self.assertIn('shopping_lists', data['tables'])
        self.assertIn('shopping_list_items', data['tables'])
        self.assertEqual(len(data['tables']['nex_messages']), 1)
        self.assertEqual(len(data['tables']['nex_conversations']), 1)


if __name__ == '__main__': unittest.main()
