import sys
import unittest
from pathlib import Path
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from cloud import Cloud
from services.market import receipt_comparison, product_values


class MarketCloudTests(unittest.TestCase):
    def test_receipt_preserves_gross_total_and_reports_difference(self):
        rows = [{'product_name': 'Arroz', 'quantity': '2.5', 'unit_price': '3.20'}]
        result = receipt_comparison(rows, '9.00', '1.00')
        self.assertEqual(result, dict(cart=Decimal('8'), receipt=Decimal('9'), cashback=Decimal('1'), difference=Decimal('1'), net=Decimal('8')))

    def test_invalid_quantities_and_cashback(self):
        for quantity in ('NaN', 'Infinity', '-1', '0', 'invalid'):
            with self.subTest(quantity=quantity), self.assertRaises(ValueError):
                product_values('Produto', quantity, '1')
        with self.assertRaises(ValueError):
            receipt_comparison([], '1', '2')

    def test_retry_only_transport_errors(self):
        cloud = Cloud()
        operation = Mock(side_effect=ValueError('schema'))
        with patch('cloud.time.sleep') as sleep, self.assertRaises(ValueError):
            cloud._run_network(operation)
        self.assertEqual(operation.call_count, 1)
        sleep.assert_not_called()
        operation = Mock(side_effect=[ConnectionError(), ['ok']])
        with patch('cloud.time.sleep'):
            self.assertEqual(cloud._run_network(operation), ['ok'])
        self.assertTrue(cloud.online)

    def test_missing_offline_cache_is_not_empty_finances(self):
        cloud = Cloud()
        cloud.user = SimpleNamespace(id='a')
        cloud.household = {'id': 'h'}
        cloud.client = Mock()
        cloud._run_network = Mock(side_effect=ConnectionError())
        with self.assertRaisesRegex(RuntimeError, 'sem cópia offline'):
            cloud.list_income('09/2026')
        cloud._cache_set('income:*, household_members(display_name)', [{'id': '1', 'month': '09/2026', 'amount': 42}])
        self.assertEqual(cloud.list_income('09/2026')[0]['amount'], 42)
        cloud.user = SimpleNamespace(id='b')
        with self.assertRaises(RuntimeError):
            cloud.list_income('09/2026')

    def test_authorization_errors_do_not_return_old_cache(self):
        cloud = Cloud()
        cloud.user = SimpleNamespace(id='a')
        cloud.household = {'id': 'h'}
        cloud.client = Mock()
        cloud._cache_set('income:*', [{'amount': 100}])
        cloud._run_network = Mock(side_effect=PermissionError())
        with self.assertRaises(PermissionError):
            cloud.fetch_all('income')


if __name__ == '__main__':
    unittest.main()
