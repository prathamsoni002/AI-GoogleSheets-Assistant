import unittest
from core.google_sheets import GoogleSheetsManager

class TestGoogleSheetsManager(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Initialize GoogleSheetsManager once for all tests
        cls.manager = GoogleSheetsManager("TEST AI")

    def test_fetch_data_all(self):
        data = self.manager.fetch_data(sheet_name='Bin')
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0, "Sheet data should not be empty")

    def test_fetch_data_specific_range(self):
        data = self.manager.fetch_data(sheet_name='Bin', cell_range='A1:B2')
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 2, "Should return 2 rows")
        self.assertEqual(len(data[0]), 2, "Each row should have 2 columns")

    def test_update_data_specific_cells(self):
        try:
            self.manager.update_data(sheet_name='Bin', data=[["Test1", "Test2"]], cell_range='A1:B1')
            result = self.manager.fetch_data(sheet_name='Sheet1', cell_range='A1:B1')
            self.assertEqual(result, [["Test1", "Test2"]], "Data in A1:B1 should match the input")
        except Exception as e:
            self.fail(f"Unexpected exception: {e}")

    def test_update_data_invalid(self):
        with self.assertRaises(ValueError):
            self.manager.update_data(sheet_name='Bin', data=None, cell_range='A1:B1')

    def test_save_to_csv(self):
        self.manager.fetch_data(sheet_name='Bin', save_to_file=True)
        import os
        file_path = 'core/fetched_data/Sheet1.csv'
        self.assertTrue(os.path.exists(file_path), "CSV file should be created")

if __name__ == '__main__':
    unittest.main()
