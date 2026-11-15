import tempfile
import unittest
from pathlib import Path
from warehouse import Warehouse
from queue_store import Queue
from replay import apply


class ReplayTests(unittest.TestCase):
    def test_two_serial_corrections(self):
        with tempfile.TemporaryDirectory() as folder:
            warehouse_path, queue_path = Path(folder) / "w.db", Path(folder) / "q.db"
            warehouse = Warehouse(warehouse_path)
            original = warehouse.accept("r1", {"station": "S1", "value": 10})
            warehouse.close()
            queue = Queue(queue_path)
            queue.add("r1", "outlier")
            queue.close()
            first = apply(warehouse_path, queue_path, "r1", "t1", {"station": "S1", "value": 13})
            second = apply(warehouse_path, queue_path, "r1", "t2", {"station": "S1", "value": 14})
            warehouse, queue = Warehouse(warehouse_path), Queue(queue_path)
            self.assertEqual([r["attempt"] for r in warehouse.rows()], [None, "t1", "t2"])
            self.assertEqual([r["payload"]["value"] for r in warehouse.rows()], [10, 13, 14])
            self.assertEqual(warehouse.original_receipt("r1"), original)
            self.assertNotEqual(first, second)
            self.assertEqual(queue.rows()[0]["receipt"], second)
            self.assertEqual(queue.rows()[0]["attempt"], "t2")
            self.assertEqual(queue.rows()[0]["state"], "closed")
            warehouse.close()
            queue.close()
