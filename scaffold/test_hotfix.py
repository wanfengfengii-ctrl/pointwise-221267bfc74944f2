import tempfile
import unittest
from pathlib import Path
from warehouse import Warehouse


class HotfixTests(unittest.TestCase):
    def test_original_retries_and_conflict(self):
        with tempfile.TemporaryDirectory() as folder:
            warehouse = Warehouse(Path(folder) / "warehouse.db")
            first = warehouse.accept("r1", {"station": "S1", "value": 10})
            self.assertEqual(warehouse.accept("r1", {"value": 10, "station": "S1"}), first)
            with self.assertRaises(ValueError):
                warehouse.accept("r1", {"station": "S1", "value": 11})
            self.assertEqual(len(warehouse.rows()), 1)
            self.assertEqual(warehouse.original_receipt("r1"), first)
            warehouse.close()
