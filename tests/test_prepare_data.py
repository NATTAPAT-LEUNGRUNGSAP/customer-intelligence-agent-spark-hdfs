import csv
import hashlib
import importlib.util
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile
from openpyxl import Workbook

MODULE = Path(__file__).resolve().parents[1] / "jobs" / "prepare_data.py"
spec = importlib.util.spec_from_file_location("prepare_data", MODULE)
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


class PrepareDataTest(unittest.TestCase):
    def test_two_sheets_preserve_missing_customer_return_and_csv_escaping(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workbook = Workbook()
            first = workbook.active
            first.title = "2009-2010"
            header = ["Invoice", "StockCode", "Description", "Quantity", "InvoiceDate", "Price", "Customer ID", "Country"]
            first.append(header)
            first.append(["100", "P1", 'Gift, "large"\nbox', 2, datetime(2010, 1, 1), 1.25, 12345, "UK"])
            second = workbook.create_sheet("2010-2011")
            second.append(header)
            second.append(["C100", "P1", "Return", -1, datetime(2011, 1, 1), 1.25, None, "UK"])
            workbook.save(root / "fixture.xlsx")
            with ZipFile(root / "online_retail_ii.zip", "w") as archive:
                archive.write(root / "fixture.xlsx", "nested/source.xlsx")
            previous_root = prepare.ROOT
            prepare.ROOT = root
            try:
                prepare.main()
                first_bytes = (root / "retail.csv").read_bytes()
                prepare.main()
                self.assertEqual(first_bytes, (root / "retail.csv").read_bytes())
            finally:
                prepare.ROOT = previous_root
            with (root / "retail.csv").open(newline="", encoding="utf-8") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["description"], 'Gift, "large"\nbox')
            self.assertEqual(rows[0]["invoice_ts"], "2010-01-01 00:00:00")
            self.assertEqual(rows[1]["customer_id"], "")
            self.assertEqual(rows[1]["quantity"], "-1")
            self.assertEqual(rows[1]["source_sheet"], "2010-2011")
            manifest = json.loads((root / "manifest.json").read_text())
            self.assertEqual(manifest["rows"], 2)
            self.assertEqual(manifest["csv_sha256"], hashlib.sha256(first_bytes).hexdigest())


if __name__ == "__main__":
    unittest.main()
