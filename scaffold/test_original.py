import tempfile
import unittest
from pathlib import Path
from warehouse import Warehouse


class OriginalTests(unittest.TestCase):
    def test_original_receipt_is_durable(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "warehouse.db"
            warehouse = Warehouse(path)
            receipt = warehouse.accept("r1", {"station": "S1", "value": 10})
            warehouse.close()
            warehouse = Warehouse(path)
            self.assertEqual(warehouse.original_receipt("r1"), receipt)
            self.assertEqual(warehouse.rows()[0]["payload"], {"station": "S1", "value": 10})
            self.assertEqual(set(receipt), {"seq", "record", "digest"})
            warehouse.close()
