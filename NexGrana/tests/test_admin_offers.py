import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from services.admin_offers import (
    OfferValidationError,
    build_offer_payload,
    filter_admin_offers,
    normalize_tags,
    parse_optional_money,
    validate_image_url,
)


class AdminOffersTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 9, 18, tzinfo=timezone.utc)
        self.valid = {
            "title": "Cafeteira Espresso LOV",
            "subtitle": "Confira voltagem e condições no parceiro.",
            "provider": "Mercado Livre",
            "url": "https://meli.la/1PQ6Tsq",
            "image_url": "https://http2.mlstatic.com/D_NQ_NP_123.jpg",
            "image_alt": "Cafeteira preta vista de frente",
            "category": "Casa e cozinha",
            "search_tags": "cafeteira, café, CAFETEIRA",
            "sort_order": "10",
            "expires_at": "2027-12-31T23:59:59Z",
            "price": "129,90",
            "enabled": True,
        }

    def test_build_payload_normalizes_safe_fields(self):
        payload = build_offer_payload(self.valid, now=self.now)
        self.assertEqual(payload["price"], 129.90)
        self.assertEqual(payload["search_tags"], ["cafeteira", "café"])
        self.assertEqual(payload["category"], "Casa e cozinha")
        self.assertEqual(payload["source"], "owner_panel")
        self.assertTrue(payload["enabled"])

    def test_edit_preserves_product_key(self):
        payload = build_offer_payload(self.valid, existing={"product_key": "stable-key"}, now=self.now)
        self.assertEqual(payload["product_key"], "stable-key")

    def test_rejects_untrusted_product_and_image_urls(self):
        for field, value in (
            ("url", "https://evil.example/item"),
            ("url", "https://user:secret@meli.la/item"),
            ("image_url", "http://http2.mlstatic.com/image.jpg"),
            ("image_url", "https://evil.example/image.jpg"),
        ):
            values = {**self.valid, field: value}
            with self.subTest(field=field, value=value), self.assertRaises(OfferValidationError):
                build_offer_payload(values, now=self.now)

    def test_image_requires_accessible_description(self):
        with self.assertRaises(OfferValidationError):
            build_offer_payload({**self.valid, "image_alt": ""}, now=self.now)

    def test_published_offer_requires_future_expiry(self):
        with self.assertRaises(OfferValidationError):
            build_offer_payload({**self.valid, "expires_at": "2026-01-01T00:00:00Z"}, now=self.now)

    def test_draft_may_be_expired_for_repair(self):
        payload = build_offer_payload(
            {**self.valid, "enabled": False, "expires_at": "2026-01-01T00:00:00Z"},
            now=self.now,
        )
        self.assertFalse(payload["enabled"])

    def test_price_and_tags_validation(self):
        self.assertEqual(parse_optional_money("1.234,56"), 1234.56)
        self.assertIsNone(parse_optional_money(""))
        self.assertEqual(normalize_tags(" casa, Casa, cozinha "), ["casa", "cozinha"])
        with self.assertRaises(OfferValidationError):
            parse_optional_money("-1")

    def test_admin_filters(self):
        rows = [
            {"title": "Cafeteira", "category": "Casa", "enabled": True},
            {"title": "Fone", "category": "Tecnologia", "enabled": False},
        ]
        self.assertEqual(len(filter_admin_offers(rows, status="published")), 1)
        self.assertEqual(filter_admin_offers(rows, query="fone")[0]["title"], "Fone")
        self.assertEqual(filter_admin_offers(rows, category="Casa")[0]["title"], "Cafeteira")

    def test_image_host_allowlist(self):
        self.assertTrue(validate_image_url(""))
        self.assertTrue(validate_image_url("https://http2.mlstatic.com/a.jpg"))
        self.assertFalse(validate_image_url("https://localhost/a.jpg"))


if __name__ == "__main__":
    unittest.main()
