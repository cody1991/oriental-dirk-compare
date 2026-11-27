import importlib.util
import unittest
from pathlib import Path
spec = importlib.util.spec_from_file_location('refresh', Path(__file__).resolve().parents[1] / 'scripts/refresh-offers.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class Specs(unittest.TestCase):
    def setUp(self):
        self.t = {'packages': {'per pak': '每包'}, 'packageByUrl': {}}
    def test_url_weight(self):
        self.assertEqual(m.package_zh('per pak', 'https://amazingoriental.com/product/example-500g/', self.t), '每包 · 500 g')
    def test_multipack_and_range(self):
        for slug, expected in [('ice-6x30g','6 × 30 g'), ('sauce-50-80g','50–80 g'), ('tea-10x25g','10 × 25 g'), ('sauce-207ml','207 ml')]:
            self.assertEqual(m.package_zh('per pak', f'https://amazingoriental.com/product/{slug}/', self.t), f'每包 · {expected}')
    def test_shrimp_grade_is_not_weight_range(self):
        self.assertEqual(m.package_zh('per pak', 'https://amazingoriental.com/product/prawns-26-30-750g/', self.t, 'Prawns 26/30'), '每包 · 750 g')
    def test_no_invented_sizes_or_duplicate(self):
        self.assertEqual(m.package_zh('per pak', 'https://amazingoriental.com/product/9661/', self.t), '每包')
        self.assertEqual(m.package_zh('per 500g', 'https://amazingoriental.com/product/meat-500g/', self.t), 'per 500g')
        self.t['packageByUrl']['url'] = '907 g'
        self.assertEqual(m.package_zh('per pak', 'url', self.t), '每包 907 g')

if __name__ == '__main__': unittest.main()
